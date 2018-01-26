import khtdirsrvlib as kht
import os, subprocess
import socket as s
from select import select
from model import Module
import random
import time


class GameServer(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.buffsize = 2048**2
        self.main_socket = s.socket(s.AF_INET, s.SOCK_STREAM)  # Create socketTCP
        ###
        self.main_socket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, self.port)
        ###
        self.main_socket.bind((self.ip, self.port))
        self.main_socket.listen(5)
        self.server_is_open = True  # is the game server on?

        self.games = []  # list of on-going games
        self.names = {}  # dictionary of client and his game name
        self.timers = {}  # dictionary of each game and its time state (True/False)  {Game:T/F}
        self.question_start_time = {}  # dictionary of {Game:current_question_start_time}
        self.wall_displays = {}  # dictionary of all wall display sockets and their games {socket:Game}
        self.next_question_request = []  # list of wall displays that requested a next question (for a specific round)
        self.validated = {}  # dictionary of clients and their validated games
        self.validated_login = {}  # dictionary of validated username and password clients, values: T/number of failed logins

        self.messages = {}  # {socket:[messages],...}

        self.inputs = [self.main_socket]
        self.outputs = []
        self.connected = {}  # dictionary of connected clients (including clients not in games) {clientobj:(Game, player_name),...}

        self.m = Module()  # module object for database interaction

    @staticmethod
    def get_current_time():
        return time.clock()

    @staticmethod
    def run_command(cmd):
        """
        Spawn new processes, connect to their input/output/error pipes, and obtain their return codes
        arg: cmd
        arg type: string
        ret type: string
        """
        return subprocess.Popen(cmd,
                                shell=True,  # not recommended, but does not open a window
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdin=subprocess.PIPE).communicate()

    @staticmethod
    def get_host_ip():
        """

        :return: the computer's ip address
        """
        ip = GameServer.run_command('ipconfig /all')[0].split("\n")
        for i in ip:
            if 'IPv4 Address' in i and '(Preferred)' in i:
                ip = i.split()[-1]
                ip = ip[0:ip.find('(')]
                break
            else:
                ip = 'localhost'  # no specific address was found use localhost
        return ip

    @staticmethod
    def get_open_ports():
        '''

        :return: first open port number
        '''
        sock = s.socket(s.AF_INET, s.SOCK_STREAM)
        sock.bind(("", 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        sock.close()
        return port

    @staticmethod
    def update_host_and_port(host, port):
        try:
            print 'Updating Server information on Kahoot_db Server...\r\nKahoot_play Server at:\r\nHost: %s; Port: %d' \
                  % (host, port)
            result = kht.update(name='YuvalStein', ip=host, port=port)
            if result['status'] == 'OK':
                print 'Information updated successfully.'
            else:
                print(result['status'])
                raise result['status']
        except Exception as e:
            print e
            print 'Connection to kahoot_db Server failed, Please manually update the client.'

    def handle_game(self):
        while self.inputs and self.server_is_open:
            readables, writeables, exceptions = select(self.inputs, self.outputs, [])

            for sockobj in readables:

                if sockobj is self.main_socket:
                    clientobj, addr = self.main_socket.accept()
                    print 'connected from', addr
                    self.inputs.append(clientobj)
                    self.outputs.append(clientobj)
                    self.messages[clientobj] = []  # this is where the clients messages will be saved
                    self.connected[clientobj] = None  # client not in game currently

                else:
                    # Client socket
                    data = None
                    try:
                        data = sockobj.recv(self.buffsize)  # receive the data the client sent
                        print 'Got', (data), 'on', id(sockobj)
                    except Exception as e:
                        print e
                    if not data:  # close connection
                        self.inputs.remove(sockobj)
                        self.outputs.remove(sockobj)
                        del self.connected[sockobj]
                        # client exits in the middle of the game
                        if sockobj in self.validated:
                            game = self.validated[sockobj]
                            player_name = self.names[sockobj]
                            del game.players[player_name]
                            if len(game.players) < 2:
                                for socketobj, player in self.names.items():
                                    if player != player_name:
                                        self.add_data(socketobj, ['error', 'Not enough players in game.'])
                                for socketobj, _game in self.wall_displays.items():
                                    if _game == game and sockobj != socketobj:
                                        self.add_data(socketobj, ['error', 'Not enough players in game.'])
                                del self.validated[sockobj]
                                del self.names[sockobj]
                                if game in self.games:
                                    del self.games[self.games.index(game)]

                        if sockobj in self.validated_login and self.validated_login[sockobj] is True:
                            del self.validated_login[sockobj]

                        # wall clients
                        if sockobj in self.wall_displays:
                            game = self.wall_displays[sockobj]
                            del self.wall_displays[sockobj]
                            # disconnect players
                            for socketobj in self.names:  # inform all connected players that game is over
                                if socketobj in self.validated and self.validated[socketobj] == game:
                                    self.add_data(socketobj, ['error', 'Wall Display died.'])
                            if game in self.games:
                                del self.games[self.games.index(game)]

                            if sockobj in self.next_question_request:
                                del self.next_question_request[self.next_question_request.index(sockobj)]

                        # update everyone with the information
                        self.send_all_data()

                    else:  # handle data
                        num = 0
                        prev_index = 0
                        tmp_data = ""
                        orig_data = data
                        for i in range(len(orig_data)):
                            if orig_data[i] == '[':
                                num += 1
                            elif orig_data[i] == ']':
                                num -= 1
                            if num == 0:
                                if prev_index == 0:
                                    tmp_data = orig_data[:i + 1]
                                else:
                                    tmp_data = orig_data[prev_index:i + 1]
                                data = eval(tmp_data)
                                self.handle_data(data, sockobj)
                                prev_index = i + 1

                        self.send_all_data()

        # self.server_is_open = False:
        self.close_clients()
        self.close()

    def handle_data(self, data, sockobj):
        if data[0] == 'close_server':
            self.server_is_open = False
        elif data[0] == 'wall_display':
            if data[1] == 'start_update':  # get important data in the beginning of the game
                self.get_connected_players(sockobj)
            elif data[1] == 'game_update':
                if data[2] == 'first_question':
                    game = self.wall_displays[sockobj]
                    game.started = True  # update boolean 'started'
                    self.timers[game] = True
                    self.question_start_time[game] = self.get_current_time()
                    # information for wall display
                    info = ['wall_display', 'game_update', 'first_question'] + self.get_current_question_info(sockobj)
                    self.add_data(sockobj, info)

                    # information for all the connected clients to this game (possible answers list)
                    current_answers = game.get_current_answers()
                    for clientobj in self.connected:
                        # if client is in the same game of the wall display
                        if self.connected[clientobj] and self.connected[clientobj][0] == self.wall_displays[sockobj]:
                            # send the client the current answers
                            self.add_data(clientobj, ['game', 'answers'] + current_answers)
                elif data[2] == 'game_update':
                    self.get_number_of_answers(sockobj)  # returns the current question and the number of answers
                elif data[2] == 'round_results':
                    self.timers[self.wall_displays[sockobj]] = False
                    self.get_round_info(sockobj)
                    self.next_question_request = []
            elif data[1] == 'next_question':
                if sockobj not in self.next_question_request:
                    game = self.wall_displays[sockobj]
                    self.timers[game] = True
                    self.question_start_time[game] = self.get_current_time()
                    game.player_answers = {}  # new round of answers
                    game.current_question += 1  # update question number
                    info = ['wall_display', 'next_question'] + self.get_current_question_info(sockobj)
                    self.next_question_request.append(sockobj)
                    self.add_data(sockobj, info)

                    # information for all the connected clients to this game (possible answers list)
                    current_answers = game.get_current_answers()
                    for clientobj in self.connected:
                        # if client is in the same game of the wall display
                        if self.connected[clientobj] and self.connected[clientobj][0] == self.wall_displays[sockobj]:
                            # send the client the current answers
                            info = ['game', 'answers'] + current_answers
                            self.add_data(clientobj, info)
            elif data[1] == 'end_questionnaire':  # game ended
                self.timers[self.wall_displays[sockobj]] = False
                self.end_game(sockobj)

            else:  # unknown data
                pass

        elif data[0] == 'game':
            if data[1] == 'answer':
                player_name = data[3]
                # check if player already gave an answer or question time is over
                if self.timers[self.validated[sockobj]]:  # don't take answer if question time is up
                    if player_name not in self.validated[sockobj].player_answers or \
                            not self.validated[sockobj].player_answers[player_name]:
                        self.update_player_answer(sockobj, data[2], player_name)

        elif data[0] == 'join':
            if data[1] == 'validate':
                self.validate_game(sockobj, data[2], data[3])
            else:  # player wants to join a game
                if sockobj in self.validated and self.validated[sockobj]:  # final validation
                    self.join_game(sockobj, self.validated[sockobj], data[1])
                    # if first player connected set automatic timer (if requested for game)
                    if len(self.validated[sockobj].players) == 1 and \
                            not self.validated[sockobj].wait_for_players:
                        self.timers[self.validated[sockobj]] = ('Start', self.get_current_time())

        elif data[0] == 'login':
            login_request = data[1]
            if login_request == 'login':  # user wants to login
                self.validate_login(sockobj, data[2], data[3])
            elif login_request == 'get_all_kahoots':
                self.add_data(sockobj, ['login', 'get_all_kahoots'] + self.m.get_all_questionnaries())
            elif login_request == 'get_my_kahoots':
                self.add_data(sockobj, ['login', 'get_my_kahoots'] + self.m.get_user_questionnaires(data[2]))
            elif login_request == 'host_game':
                self.open_new_game(sockobj, data[2])
            else:  # create new game (not to play right now)
                self.create_new_game(sockobj, data[2], data[3], data[4], data[5])

        elif data[0] == 'sign_up':
            self.add_new_user(sockobj, data[1], data[2])

        else:  # invalid request
            self.add_data(sockobj, 'Invalid request')

    def initiate(self):
        self.main_socket.bind((self.ip, self.port))
        self.main_socket.listen(4)

    def add_data(self, socketobj, data):
        if type(data) != list:
            data = [data]
        self.messages[socketobj] += data

    def send_all_data(self):
        for socketobj in self.messages:
            if self.messages[socketobj]:
                data = str(self.messages[socketobj])
                try:
                    socketobj.send(data)
                except:
                    pass
                # delete the sent data
                self.messages[socketobj] = []

    def validate_game(self, socketobj, game_name, game_pin):
        game = None
        info = None
        for g in self.games:
            # if game name and pin are correct, and the game hasn't started yet then joining is valid
            if str(g.name) == str(game_name) and str(g.pin) == str(game_pin):
                    if not g.started:
                        self.validated[socketobj] = g  # validate game for client
                        game = g
                    else:
                        info = 'game in progress, no more new players accepted'
        if game and not info:
            self.add_data(socketobj, ['join', 'request', True])
        else:
            self.add_data(socketobj, ['join', 'request', False])
            if not info:
                info = "couldn't find requested game, please check the name and pin."
            data = [{'join': info}]
            self.add_data(socketobj, data)

    def validate_login(self, socketobj, username, password):
        correct_password = self.m.get_user_password(username)
        if correct_password and correct_password == password:  # correct password was entered
            self.validated_login[socketobj] = True
            self.add_data(socketobj, ['login', 'login', True])  # return client successful login
        elif not correct_password:  # no such user in database
            self.add_data(socketobj, ['login', 'login', False, 'User not found'])
        else:
            self.validated_login[socketobj] = self.validated_login[socketobj] + 1 if socketobj in self.validated_login \
                else 1  # number of unsuccessful login attempts
            self.add_data(socketobj, ['login', 'login', False])  # return client unsuccessful

    def create_new_game(self, socketobj, publisher, game_name, questions_and_answers, correct_answers_and_times):
        result = self.m.add_new_questionnaire(publisher, game_name, questions_and_answers, correct_answers_and_times)
        if result:
            self.add_data(socketobj, 'successfully added new questionnaire')
        else:
            self.add_data(socketobj, "couldn't add the questionnaire because name is not unique, "
                                     "please choose a different name.")

    def open_new_game(self, socketobj, game_name):
        print 'Opening new game...'
        game_pin = random.randrange(10**5, 10**6)  # game_pin is a random number between 100000 and 999999
        print 'Game Name: ',game_name,'; Game Pin:', game_pin
        game = Game(game_name, game_pin)
        self.games.append(game)
        self.wall_displays[socketobj] = game
        game.match_question_and_answer(self.m.get_questions_and_answers(game_name))  # update game questions
        # timing settings
        time_settings = eval(self.m.get_time_settings(game_name))  # dictionary of time settings
        game.wait_for_players = time_settings['wait_for_players']
        game.interval_between_questions = time_settings['interval']
        # get starting info and update the wall display
        self.add_data(socketobj, ['login', 'host_game', game_pin, game.wait_for_players, game.interval_between_questions])

    def join_game(self, socketobj, game, player_name):
        if player_name not in game.players:
            game.players[player_name] = 0  # every player starts with 0 points
            self.names[socketobj] = player_name
            self.connected[socketobj] = (game, player_name)  # save the player and the game he is connected to
            self.add_data(socketobj, ['join', True, player_name,
                                      'Successfully added to game!\r\nWaiting for more players...'])
        else:
            self.add_data(socketobj, ['join', False, player_name, 'Name already taken, please choose a different name'])

    def get_connected_players(self, socketobj):
        game = self.wall_displays[socketobj]
        players_in_game = str(game.players)
        self.add_data(socketobj, ['wall_display', 'start_update', players_in_game])

    def get_number_of_answers(self, socketobj):
        game = self.wall_displays[socketobj]
        all_answers = len(game.player_answers)
        self.add_data(socketobj, ['wall_display', 'game_update', 'game_update', str(all_answers)])

    def get_round_info(self, socketobj):
        game = self.wall_displays[socketobj]
        # change the current question and immediately return to what it was before,
        # in order to check if their is a next question
        game.current_question += 1
        if game.get_current_question() == [None]:  # last question
            info = ['wall_display', 'game_update', 'round_results', game.get_game_scores(), True]
        else:  # their is another question after this one
            info = ['wall_display', 'game_update', 'round_results', game.get_game_scores(), False]
        game.current_question -= 1
        self.add_data(socketobj, info)

        # update all the connected clients if they were right or wrong, and give them their scores.
        for clientobj in self.connected:
            # if client is in the same game of the wall display
            if self.connected[clientobj] and self.connected[clientobj][0] == game:
                # send the client the current answers
                player_name = self.names[clientobj]
                if player_name in game.player_answers:
                    client_answer = game.player_answers[player_name] in game.correct_answers[game.current_question]
                else:
                    client_answer = False
                points = game.players[player_name]
                self.add_data(clientobj, ['game', 'round_results', client_answer, points])

    def update_player_answer(self, socketobj, answer, player_name):
        game = self.validated[socketobj]
        correct_answer = game.correct_answers[game.current_question]
        # single answer or multiple correct answers
        if (type(correct_answer) == str and answer == correct_answer) or (answer in correct_answer):
            points = self.calculate_points(True, self.question_start_time[game], self.get_current_time(),
                                           game.times[game.current_question])
            if player_name in game.correct_player_answers:
                game.correct_player_answers[player_name] += 1
            else:  # first correct answer for player
                game.correct_player_answers[player_name] = 1
        else:
            points = self.calculate_points(False)
        game.update_player_and_points(player_name, points)
        game.player_answers[player_name] = answer  # player gave an answer, don't allow more

    def calculate_points(self, answer, start_time=None, time=None, question_time=None):
        if not answer:  # if answer was incorrect don't give the player any points
            return 0
        time_left = question_time - (time - start_time)
        return int(100*(time_left/question_time))

    def get_current_question_info(self, socketobj):
        game = self.wall_displays[socketobj]
        all_answers = len(game.player_answers)
        info = [str(all_answers)] + game.get_current_question()
        return info

    def add_new_user(self, socketobj, username, password):
        result = self.m.add_user(username, password)
        if result == 'user added successfully':
            self.add_data(socketobj, ['sign_up', True])
        else:  # username taken
            result += "Please enter a different username."
            self.add_data(socketobj, ['sign_up', False, result])

    def message_all_game_participants(self, game, message):
        # message clients
        for sockobj in self.validated:
            if self.validated[sockobj] == game:
                self.add_data(sockobj, message)
        # message all wall display clients
        for sockobj in self.wall_displays:
            if self.wall_displays[sockobj] == game:
                self.add_data(sockobj, message)

    def client_score(self, client):
        return self.validated[client].players[self.names[client]]

    def end_game(self, socketobj):
        game = self.wall_displays[socketobj]
        game.ended = True
        info = ['wall_display', 'end_questionnaire', game.get_winners()]
        self.add_data(socketobj, info)
        #self.save_game(game)  # if game ended and more than 2 players where in it, save the game

        # send players their places
        clients = []
        for clientobj in self.connected:
            # if client is in the same game of the wall display
            if self.connected[clientobj] and self.connected[clientobj][0] == game:
                clients.append(clientobj)

        clients = sorted(clients, key=self.client_score, reverse=True)
        for i in range(len(clients)):
            player_name = self.names[clients[i]]
            points = game.players[player_name]
            self.add_data(clients[i], ['game', 'final_results', i+1, points])

    def save_game(self, game):
        if len(game.players) >= 2 and game.ended:
            self.m.add_questionnaire(self.m.get_all_info(game.name)[0][0], self.m.get_all_info(game.name)[0][1],
                                     self.m.get_all_info(game.name)[0][2], game.players,
                                     self.m.get_all_info(game.name)[0][-3])

    def close_clients(self):
        print 'Sending Shut-Down'
        for client in self.connected:
            client.send(str(['server_down']))

    def close(self):
        self.main_socket.close()


class Game(object):
    def __init__(self, game_name, game_pin):
        self.name = game_name
        self.pin = game_pin
        self.started = False
        self.ended = False
        self.wait_for_players = True  # if false, waits for 30 seconds after one player is connected
        self.interval_between_questions = True  # if false wait 10 seconds before displaying the next question
        self.questions = []
        self.current_question = 0  # question pointer
        self.answers = []  # list of lists (all answers)
        self.correct_answers = []  # list of lists (only correct answers)
        self.times = []  # timers, starts from the first question
        self.players = {}  # saves the game players and scores
        self.player_answers = {}  # saves the players answers each round so that no more than one answer is accepted
        self.correct_player_answers = {}  # saves the number of correct answers per player

    def match_question_and_answer(self, questions_and_answers):
        '''

        :param questions_and_answers: data from database about the questionnaire
        :return: sorts the data into the questions, answers and times of the game instance
        '''
        # append all the game question in order and update question times
        num = 1
        questions_and_answers = [eval(questions_and_answers[0]), eval(questions_and_answers[1])]
        while len(questions_and_answers[1]) != len(self.questions):
            for questions in questions_and_answers[1]:
                # questions_and_answers[1][questions] is a tuple of (question, time)
                if questions_and_answers[1][questions][0] == num:
                    self.questions.append(questions)
                    self.times.append(questions_and_answers[1][questions][1])  # the time for the question
                    num += 1

        # append all the game answers in order
        # note: there may be more than one correct answer
        for questions in self.questions:
            answers = []
            correct_answers = []
            for answer in questions_and_answers[0][questions]:
                # answers is a tuple of (answer, T/F)
                if answer[1]:  # True, answer is correct
                    correct_answers.append(answer[0])
                answers.append(answer[0])
            self.answers.append(answers)  # all answers
            self.correct_answers.append(correct_answers)  # correct answers

    def del_player(self, player):
        if player in self.players:
            del self.players[player]

    def update_player_and_points(self, player_name, points=None):
        """

        :param player_name: string
        :param points: int
        :return: updates the player's points
        """

        if player_name in self.players:
            self.players[player_name] += points
        else:  # new player / first answer
            self.players[player_name] = points

    def get_current_question(self):
        if self.current_question < len(self.questions):
            current_question = [self.questions[self.current_question], self.answers[self.current_question],
                                self.correct_answers[self.current_question], self.times[self.current_question]]
        else:  # no more questions, end of game
            self.ended = True
            current_question = [None]
        return current_question

    def get_current_answers(self):
        if self.current_question < len(self.questions):
            return [self.answers[self.current_question]]
        else:
            return [None]

    def get_current_timer(self):
        if self.times:
            return self.times[self.current_question]
        return [None]

    def get_game_scores(self):
        """

        :return: an organized list from the highest to the lowest in rank
        """
        return [(key, value) for key, value in sorted(self.players.items(), reverse=True)]

    def get_winners(self):
        """

        :return: the first 3 highest players
        """
        scores = self.players.copy()  # create a copy dictionary to work on
        winners = []
        num = 0
        while scores and num < 3:
            winner = max(scores)
            num_of_correct_answers = 0
            if winner in self.correct_player_answers:
                num_of_correct_answers = self.correct_player_answers[winner]
            winners.append((winner, scores[winner], num_of_correct_answers))
            del scores[winner]  # find next place winner
            num += 1
        return winners  # list of winners and their scores


def main():
    """
    server = GameServer(GameServer.get_host_ip(), GameServer.get_open_ports())
    server.update_host_and_port(server.ip, server.port)
    server.handle_game()"""

    myHost = GameServer.get_host_ip()
    myPort = 49990
    server = GameServer(myHost, myPort)
    server.update_host_and_port(myHost, myPort)
    server.handle_game()

if __name__ == '__main__':
    main()
