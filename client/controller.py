import socket as s
import khtdirsrvlib as kht
import Tkinter as tk
import ttk
import tkMessageBox
import Dialog
import time


class GameClient(tk.Tk):
    parm = False

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        # ip and port are generally taken from the kahoot_db server.
        # if some problem occurs in getting this information from the server,
        # manually update the following information about the kahoot_Play server:
        ip = '192.168.56.1'
        port = 49990

        self.socket = GameClient.connect_to_server(self, ip, port)  # tcp socket connection
        if self.socket:
            self.socket.setblocking(0)  # set tcp client Socket to no blocking socket
        self.BUFSIZ = 2048**2

        tk.Tk.iconbitmap(self, default="kahoot_gmE_icon.ico")
        tk.Tk.title(self, "Kahoot")

        # the container is where we'll stack a bunch of frames
        # on top of each other, then the one we want visible
        # will be raised above the others
        self.container = tk.Frame(self)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Set window min size, and align window to center
        self.align_window_to_center(300, 200)
        self.update_idletasks()
        self.after_idle(lambda: self.minsize(self.winfo_width(), self.winfo_height()))

        self.frames = {}
        for F in (StartPage, GameDialog, LoginDialog, UserHomePage, PassTime, GameTemplate, SignUpDialog,
                  SuccessfulSignUp):
            self.initialize_frame(F)

        self.show_frame(page_name="StartPage")

    '''SERVER-CLIENT RELATED METHODS'''

    def connect_to_server(self, ip, port):
        try:
            result = kht.get_details('YuvalStein')
            if result['status'] == 'OK':
                ip = result['result']['ipaddr']
                port = result['result']['port']
        except:
            self.show_error('Connection error', "Error in connection to Kahoot_db server")
        try:
            socket = s.socket(s.AF_INET, s.SOCK_STREAM)
            socket.connect((ip, port))
        except Exception as e:
            socket = None
            self.show_error('Connection error', "Error in connection to Kahoot_Play server:\r\n" + str(e))
        finally:
            return socket

    def send_data(self, data):
        try:
            self.socket.send(str(data))
        except:
            self.show_error('Problem with Server', 'Cannot connect to server...')

    def recv_data(self):
        # wait max 10 seconds before returning the data
        start_time = time.clock()
        while time.clock()-start_time <= 10:
            try:
                data = self.socket.recv(self.BUFSIZ)
                if data:
                    result = self.handle_data(eval(data))  # handle the received data from the server
                    return result
            except:
                time.sleep(0.1)
        return None

    def handle_data(self, data):
        if data[0] == 'server_down':
            return data
        elif data[0] == 'error':
            return data
        elif data[0] == 'sign_up':
            return data[1:]
        elif data[0] == 'login':
            if data[1] == 'login':  # login response
                return data[2:]
            elif data[1] == 'get_all_kahoots' or data[1] == 'get_my_kahoots':
                return data[2:]
        elif 'join' in data:
            if data[1] == 'request':
                return data[2:]
            else:  # player name validation for game
                return data[1:]

        return None

    def add_user(self, username, password):
        self.send_data(['sign_up', username, password])
        response = self.recv_data()
        return response

    def validate_game(self, game_pin, game_name):
        self.send_data(['join', 'validate', game_name, game_pin])
        response = self.recv_data()
        return response  # true or false (unsuccessful message)

    def validate_user(self, username, password):
        self.send_data(['login', 'login', username, password])
        response = self.recv_data()
        return response  # true or false, or None

    def get_my_kahoots(self, username):
        self.send_data(['login', 'get_my_kahoots', username])
        response = self.recv_data()
        return response

    def get_all_kahoots(self):
        self.send_data(['login', 'get_all_kahoots'])
        response = self.recv_data()
        return response

    '''TKINTER-VIEW RELATED METHODS'''

    def show_error(self, title, message, opt=True):
        if opt:
            self.withdraw()
            tkMessageBox.showwarning(title, message)
            self.deiconify()
        else:
            tkMessageBox.showwarning(title, message)

    def initialize_frame(self, class_name, **kwargs):
        page_name = class_name.__name__
        if kwargs:
            frame = class_name(self.container, self, **kwargs)
        else:
            frame = class_name(self.container, self)
        self.frames[page_name] = frame

        # put all of the pages in the same location;
        # the one on the top of the stacking order
        # will be the one that is visible.
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_rowconfigure(0, weight=1, minsize=20)
        frame.grid_columnconfigure(0, weight=1, minsize=20)

    def align_window_to_center(self, width, height):
        x = self.winfo_screenwidth() / 2 - 0.5 * width
        y = self.winfo_screenheight() / 2 - 0.5 * height
        self.geometry("%dx%d+%d+%d" % (width, height, x, y))

    def update_size(self, width, height):
        self.minsize(width, height)
        self.align_window_to_center(width, height)
        self.update_idletasks()
        self.after_idle(lambda: self.minsize(width, height))

    def update_title(self, title):
        self.title(title)

    def show_frame(self, frame=None, page_name=None):
        '''Show a frame for the given page name (or for the given frame)'''
        if not frame:
            frame = self.frames[page_name]
        frame.tkraise()
        self.update()

    def handle_frame(self, page_name):
        '''Take care of the frame before displaying it (if needed)'''
        frame = self.frames[page_name]

        if page_name == "GameDialog":
            GameClient.parm = True
            result = frame.start_dialog()
            if result == "cancelled":  # cancel button was pressed
                self.show_frame(page_name="StartPage")  # return to home page
            else:  # validate game request
                self.show_frame(page_name="PassTime")
                self.update()
                response = self.validate_game(result[0], result[1]) if result else None
                if not response:
                    self.show_error("Connection Error", "Cannot connect to server.")
                    self.show_frame(page_name="StartPage")
                elif response and response[0] == 'server_down':
                    self.show_error('SERVER IS CLOSED', 'Server is now closed.')
                    self.show_frame(page_name="StartPage")
                    self.update_title('Welcome to Kahoot')
                    self.update_size(300, 200)
                    self.update()
                elif response and response[0] == 'error':
                    self.show_error('Game Error', response[1])
                    self.show_frame(page_name="StartPage")
                    self.update_title('Welcome to Kahoot')
                    self.update_size(300, 200)
                    self.update()
                elif response and response[0]:
                    self.initialize_frame(GamePageHandler, game_name=result[1])
                    self.update()
                else:
                    message = response[1]['join']
                    self.show_frame(page_name="StartPage")
                    self.update()
                    self.show_error("Game Error", message, opt=False)

        elif page_name == "LoginDialog":
            GameClient.parm = True
            result = frame.start_dialog()
            if result == "cancelled":  # cancel button was pressed
                self.show_frame(page_name="StartPage")  # return to home page
            else:  # validate login
                self.show_frame(page_name="PassTime")
                self.update()
                response = self.validate_user(result[0], result[1]) if result else None
                if not response:
                    self.show_error("Connection Error", "Cannot connect to server.")
                    self.show_frame(page_name="StartPage")
                elif response and response[0] == 'server_down':
                    self.show_error('SERVER IS CLOSED', 'Server is now closed.')
                    self.show_frame(page_name="StartPage")
                    self.update_title('Welcome to Kahoot')
                    self.update_size(300, 200)
                    self.update()
                elif response and response[0] == 'error':
                    self.show_error('Game Error', response[1])
                    self.show_frame(page_name="StartPage")
                    self.update_title('Welcome to Kahoot')
                    self.update_size(300, 200)
                    self.update()
                elif response and response == [True]:  # if user and password are correct
                    # get user kahoots, as well as all other kahoots
                    self.initialize_frame(UserHomePage, username=result[0], my_kahoots=self.get_my_kahoots(result[0]),
                                          all_kahoots=self.get_all_kahoots(), resize=True)
                    self.show_frame(page_name='UserHomePage')
                    self.update_title('Welcome %s' % result[0])
                    self.update()
                else:
                    if not response:
                        self.show_error('Server Problem', 'Server did not respond after 10 seconds.', opt=False)
                    elif response and len(response) == 2:
                        self.show_error(response[1], 'User does not exist. Please sign up in order to login.', opt=False)
                    else:
                        self.show_error('Wrong Username/Password Entered', 'Please try again.', opt=False)
                    self.show_frame(page_name="StartPage")  # return to home page
                    self.update()

        elif page_name == "SignUpDialog":
            GameClient.parm = True
            result = frame.start_dialog()
            if result == "cancelled":  # cancel button was pressed
                self.show_frame(page_name="StartPage")  # return to home page
            else:  # add user
                self.show_frame(page_name="PassTime")
                self.update()
                response = self.add_user(result[0], result[1]) if result else None
                if not response:
                    self.show_error("Connection Error", "Cannot connect to server.")
                    self.show_frame(page_name="StartPage")
                elif response and response[0] == 'server_down':
                    self.show_error('SERVER IS CLOSED', 'Server is now closed.')
                    self.show_frame(page_name="StartPage")
                    self.update_title('Welcome to Kahoot')
                    self.update_size(300, 200)
                    self.update()
                elif response and response[0] == 'error':
                    self.show_error('Game Error', response[1])
                    self.show_frame(page_name="StartPage")
                    self.update_title('Welcome to Kahoot')
                    self.update_size(300, 200)
                    self.update()
                elif response and response[0]:
                    self.show_frame(page_name="SuccessfulSignUp")
                    self.update()
                else:
                    if response:
                        message = response[1]
                        self.show_frame(page_name="StartPage")
                        self.show_error("Game Error", message, opt=False)
                        self.update()

        elif page_name == "StartPage":
            self.update_title("Kahoot")  # update to home page title
            self.show_frame(page_name="StartPage")
            self.update_size(300, 200)
            self.update()

        else:
            frame.tkraise()


class StartPage(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        join_game_btn = ttk.Button(self, text="Join a Game",
                                   command=lambda: controller.handle_frame("GameDialog"))
        login_btn = ttk.Button(self, text="Login",
                               command=lambda: controller.handle_frame("LoginDialog"))
        sign_up_btn = ttk.Button(self, text="Sign Up",
                                 command=lambda: controller.handle_frame("SignUpDialog"))

        join_game_btn.grid(row=0, column=0, columnspan=8, rowspan=2, sticky="ewns", pady=5, padx=5)
        login_btn.grid(row=2, column=0, columnspan=4, rowspan=2, sticky="ewns", pady=5, padx=5)
        sign_up_btn.grid(row=2, column=4, columnspan=4, rowspan=2, sticky="ewns", pady=5, padx=5)

        self.controller.update_size(300, 200)
        self.update()


class SignUpDialog(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self)
        label.pack()

    def start_dialog(self):
        d = Dialog.Dialog(self, title="Sign Up", parm=GameClient.parm, text1="Username:", text2="Password:")
        return d.result


class SuccessfulSignUp(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        label = ttk.Label(self, text='Successfully signed up!\r\nNow Login to start playing and making kahoots!')
        label.pack()
        back_btn = ttk.Button(self, text='Back', command=lambda: controller.handle_frame("StartPage"))
        back_btn.pack(pady=20)


class GameDialog(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self)
        label.pack()

    def start_dialog(self):
        d = Dialog.Dialog(self, title="Kahoot Game", parm=GameClient.parm, text1="Game Pin:", text2="Game Name:")
        return d.result


class GamePageHandler(tk.Frame):

    def __init__(self, parent, controller, game_name):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.game_name = game_name
        self.player_name = None

        self.controller.initialize_frame(GamePageEntry, game_name=self.game_name)
        self.controller.show_frame(page_name="GamePageEntry")

        self.controller.update_size(400, 150)

        self.wait_on_recv = 100  # milliseconds
        self.controller.socket.setblocking(0)
        self.controller.after(self.wait_on_recv, self.get_data)

        self.answer = None
        self.game_ended = False

        self.current_question_number = 0
        self.controller.update_title(self.game_name)

        # waiting messages

        self.waiting_messages = ["Pure genius or guesswork?", "Were you too fasssttt??"]  #TODO

    def get_data(self):
        if not self.game_ended:
            try:
                data = self.controller.socket.recv(self.controller.BUFSIZ)
                num = 0
                prev_index = 0
                tmp_data = ""
                for i in range(len(data)):
                    if data[i] == '[':
                        num += 1
                    elif data[i] == ']':
                        num -= 1
                    if num == 0:
                        if prev_index == 0:
                            tmp_data = data[:i+1]
                        else:
                            tmp_data = data[prev_index:i+1]
                        self.handle_data(eval(tmp_data))
                        prev_index = i + 1
            except Exception as e:
                if str(e) != '[Errno 10035] A non-blocking socket operation could not be completed immediately':
                    print e
            finally:
                self.controller.after(self.wait_on_recv, self.get_data)

    def handle_data(self, data):
        if data[0] == 'server_down':
            self.controller.show_error('SERVER IS CLOSED', 'Server is now closed.')
            self.controller.show_frame(page_name="StartPage")
            self.controller.update_title('Welcome to Kahoot')
            self.controller.update_size(300, 200)
            self.controller.update()

        elif data[0] == 'error':
            self.controller.show_error('Game Error', data[1])
            self.controller.show_frame(page_name="StartPage")
            self.controller.update_title('Welcome to Kahoot')
            self.controller.update_size(300, 200)
            self.controller.update()

        elif data[0] == 'join':
            if data[1]:
                self.player_name = data[2]
                self.controller.initialize_frame(PassTime, text=data[3])
                self.controller.show_frame(page_name="PassTime")
                self.update()
            else:
                self.controller.show_frame(page_name="GamePageEntry")
                self.controller.update()
                # show error (client is not yet in the game)
                self.controller.show_error('Invalid Name', data[2], False)

        elif data[0] == 'game':
            if data[1] == 'answers':
                self.current_question_number += 1
                self.controller.initialize_frame(GamePageAnswers, game_name=self.game_name,
                                                 player_name=self.player_name, current_answers=data[2],
                                                 question_number=self.current_question_number)
                self.controller.show_frame(page_name="GamePageAnswers")
                self.controller.update()

            elif data[1] == 'round_results':
                self.controller.initialize_frame(GamePageResults, result=data[2], points=data[3])
                self.controller.show_frame(page_name="GamePageResults")
                self.controller.update()

            elif data[1] == 'final_results':
                self.game_ended = True
                self.controller.initialize_frame(GamePageFinalResults, place=data[2], points=data[3])
                self.controller.show_frame(page_name="GamePageFinalResults")
                self.controller.update()


class GamePageEntry(tk.Frame):
    def __init__(self, parent, controller, game_name=None):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.game_name = game_name
        if self.game_name:
            self.controller.update_title(self.game_name)

        self.name_frame = tk.Frame(self)
        self.name_frame.pack(fill="both", expand=True)
        self.name_frame.columnconfigure(0, weight=1)
        self.name_frame.rowconfigure(0, weight=1)

        self.game_name_label = ttk.Label(self.name_frame, text="Enter your Game Name:")
        self.game_name_label.pack(expand=True)

        self.game_name_entry = ttk.Entry(self.name_frame)
        self.game_name_entry.pack(expand=True)

        self.game_name_enter_btn = ttk.Button(self.name_frame, text="Enter", command=self.send_player_name)
        self.game_name_enter_btn.pack(expand=True)

        self.name_frame.bind("<Return>", self.send_player_name)

    def send_player_name(self, event=None):
        """

        :return: function checks the name before sending it to the server
        """
        player_name = self.game_name_entry.get()
        if player_name:
            self.controller.send_data(str(['join', str(player_name)]))
        else:
            self.controller.show_error('Invalid Name', 'Please enter a name', False)


class GamePageAnswers(tk.Frame):
    def __init__(self, parent, controller, game_name=None, player_name=None, current_answers=None, question_number=0):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.game_name = game_name
        self.player_name = player_name
        self.current_answers = current_answers
        self.answers = {}  # dictionary of btn and its corresponding answer
        self.question_number = question_number

        self.game_page_frame = tk.Frame(self)
        self.game_page_frame.pack(fill="both", expand=True)
        self.top_frame = tk.Frame(self.game_page_frame)
        self.bottom_frame = tk.Frame(self.game_page_frame)
        self.top_frame.pack(side=tk.TOP, fill="both", expand=True)
        self.bottom_frame.pack(side=tk.TOP, fill="both", expand=True)

        red_answer_button = tk.Button(self.top_frame, bg="red", relief="groove", activebackground="red")
        blue_answer_button = tk.Button(self.top_frame, bg="blue", relief="groove", activebackground="blue")
        green_answer_button = tk.Button(self.bottom_frame, bg="green", relief="groove", activebackground="green")
        yellow_answer_button = tk.Button(self.bottom_frame, bg="yellow", relief="groove", activebackground="yellow")

        red_answer_button.pack(side=tk.LEFT, fill="both", expand=True, pady=5, padx=5)
        blue_answer_button.pack(side=tk.LEFT, fill="both", expand=True, pady=5, padx=5)
        green_answer_button.pack(side=tk.LEFT, fill="both", expand=True, pady=5, padx=5)
        yellow_answer_button.pack(side=tk.LEFT, fill="both", expand=True, pady=5, padx=5)

        red_answer_button.bind("<ButtonRelease>", self.send_answer)
        blue_answer_button.bind("<ButtonRelease>", self.send_answer)
        green_answer_button.bind("<ButtonRelease>", self.send_answer)
        yellow_answer_button.bind("<ButtonRelease>", self.send_answer)

        # match buttons to answers
        index = 0
        for btn in (red_answer_button, blue_answer_button, green_answer_button, yellow_answer_button):
            if self.current_answers[index]:
                self.answers[btn] = self.current_answers[index]
            index += 1

        # update question number in the title
        title = self.game_name + "    " + self.player_name + "    Question #" + str(self.question_number)
        self.controller.update_title(title)

    def send_answer(self, event):
        pressed_btn = event.widget
        answer = self.answers[pressed_btn]
        self.cancel_answers()
        self.controller.send_data(['game', 'answer', answer, self.player_name])

    def cancel_answers(self):
        """

        :return: function greys out all the answers
        """
        for btn in self.answers:
            btn['state'] = tk.DISABLED
            btn.update()


class GamePageResults(tk.Frame):
    def __init__(self, parent, controller, result, points):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.result_frame = tk.Frame(self)
        self.result_frame.pack(fill="both", expand=True)
        self.result_frame.columnconfigure(0, weight=1)
        self.result_frame.rowconfigure(0, weight=1)

        if result:
            answer_label = ttk.Label(self.result_frame, text='CORRECT!')
        else:
            answer_label = ttk.Label(self.result_frame, text='WRONG...')
        answer_label.pack(side=tk.TOP, expand=True, fill="both")

        points_label = ttk.Label(self.result_frame, text='Score: %s' % str(points))
        points_label.pack(side=tk.TOP, expand=True, fill="both")


class GamePageFinalResults(tk.Frame):
    def __init__(self, parent, controller, place, points):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.final_result_frame = tk.Frame(self)
        self.final_result_frame.pack(fill="both", expand=True)
        self.final_result_frame.columnconfigure(0, weight=1)
        self.final_result_frame.rowconfigure(0, weight=1)

        if place == 1:
            place_label = ttk.Label(self.final_result_frame, text='First Place!!!\r\nCongratulations!!!')
        elif place == 2:
            place_label = ttk.Label(self.final_result_frame, text='Second Place!!\r\nGreat Job!!')
        elif place == 3:
            place_label = ttk.Label(self.final_result_frame, text='Third Place!\r\nNice Work!')
        elif place >= 5:
            place_label = ttk.Label(self.final_result_frame, text='Top Five!\r\nGreat!')
        elif place >= 10:
            place_label = ttk.Label(self.final_result_frame, text='Top Ten!\r\nNot bad...')
        else:
            place_label = ttk.Label(self.final_result_frame, text='%s Place' % str(place))
        place_label.pack(side=tk.TOP, expand=True, fill="both")

        points_label = ttk.Label(self.final_result_frame, text='Score: %s' % str(points))
        points_label.pack(side=tk.TOP, expand=True, fill="both")

        back_btn = ttk.Button(self.final_result_frame, text='Back', command=lambda: controller.handle_frame("StartPage"))
        back_btn.pack(side=tk.TOP, expand=True, fill="both")


class LoginDialog(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self)
        label.pack()

    def start_dialog(self):
        d = Dialog.Dialog(self, title="Kahoot Game", parm=GameClient.parm, text1="User Name:", text2="Password:", opt=True)
        return d.result


class PassTime(tk.Frame):

    def __init__(self, parent, controller, text=None):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        label = ttk.Label(self, text=text) if text else ttk.Label(self, text='Just a Sec, Loading...')
        label.grid()


class UserHomePage(tk.Frame):

    def __init__(self, parent, controller, username=None, my_kahoots=None, all_kahoots=None, resize=False):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.username = username
        self.my_kahoots = my_kahoots
        self.all_kahoots = all_kahoots

        if resize:
            self.controller.update_size(400, 400)

        self.frame = tk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nesw")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # create the notebook
        self.nb = ttk.Notebook(self.frame, name='notebook')
        self.nb.grid(row=0, column=0, rowspan=4, columnspan=2, sticky="news")

        # extend bindings to top level window allowing
        #   CTRL+TAB - cycles through tabs
        #   SHIFT+CTRL+TAB - previous tab
        #   ALT+K - select tab using mnemonic (K = underlined letter)
        self.nb.enable_traversal()

        '''CREATE WIDGETS'''

        '''_create_buttons'''
        row_num = 0
        if self.username == 'admin':  # increase functionality
            self.start_btn = ttk.Button(self.frame, text='Close Server', command=self.close_server)
            self.start_btn.grid(row=row_num, column=2, sticky="sew", pady=10)
            row_num+=1

        self.start_btn = ttk.Button(self.frame, text='Start a Game', command=self.host_game)
        self.start_btn.grid(row=row_num, column=2, sticky="sew", pady=10)

        self.create_game_btn = ttk.Button(self.frame, text='Create a Game',
                                          command=lambda: controller.handle_frame("GameTemplate"), state=tk.DISABLED)
        row_num += 1
        self.create_game_btn.grid(row=row_num, column=2, sticky="sew", pady=10)

        self.edit_game_btn = ttk.Button(self.frame, text='Edit a Game', command=self.edit_game, state=tk.DISABLED)
        row_num += 1
        self.edit_game_btn.grid(row=row_num, column=2, sticky="sew", pady=10)

        self.sign_out_btn = ttk.Button(self.frame, text='Sign Out', command=self.sign_out)
        row_num += 1
        self.sign_out_btn.grid(row=row_num, column=2, sticky="sew", pady=10)

        '''_create_my_kahoots_tab'''

        self.my_kahoots_frame = tk.Frame(self.nb)
        self.my_kahoots_frame.rowconfigure(0, weight=1)
        self.my_kahoots_frame.columnconfigure(0, weight=1)

        # widgets to be displayed on 'My Kahoots' tab

        self.my_kahoots_listbox = tk.Listbox(self.my_kahoots_frame)
        self.scroll_bar = ttk.Scrollbar(self.my_kahoots_frame, orient=tk.VERTICAL, command=self.my_kahoots_listbox.yview)
        self.my_kahoots_listbox['yscroll'] = self.scroll_bar.set
        self.scroll_bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.my_kahoots_listbox.pack(fill=tk.BOTH, expand=tk.Y)

        if self.my_kahoots:
            for game_name in self.my_kahoots:
                self.my_kahoots_listbox.insert(tk.END, game_name)
        self.sort_list(self.my_kahoots_listbox)

        # add to notebook (underline = index for short-cut character)
        self.nb.add(self.my_kahoots_frame, text='My Kahoots', underline=0, padding=2)

        '''_create_all_kahoots_tab'''

        self.all_kahoots_frame = tk.Frame(self.nb)
        self.all_kahoots_frame.rowconfigure(0, weight=1)
        self.all_kahoots_frame.columnconfigure(0, weight=1)

        # widgets to be displayed on 'All Kahoots' tab

        self.all_kahoots_listbox = tk.Listbox(self.all_kahoots_frame)
        self.scroll_bar = ttk.Scrollbar(self.all_kahoots_frame, orient=tk.VERTICAL, command=self.all_kahoots_listbox.yview)
        self.all_kahoots_listbox['yscroll'] = self.scroll_bar.set
        self.scroll_bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.all_kahoots_listbox.pack(fill=tk.BOTH, expand=tk.Y)

        if self.all_kahoots:
            for game_name in self.all_kahoots:
                self.all_kahoots_listbox.insert(tk.END, game_name)
        self.sort_list(self.all_kahoots_listbox)

        # add to notebook (underline = index for short-cut character)
        self.nb.add(self.all_kahoots_frame, text='All Kahoots', underline=0, padding=2)

        '''_create_help_tab(self, nb):'''

        self.about_frame = tk.Frame(self.nb)

        self.text = [
            "Press one of the kahoots under 'My Kahoots' or under 'All Kahoots'. "
            "Then double click it to host the game, or press one of the options ",
            "on the side. Play, Create and Edit your kahoots! ",
            "\r\nEnjoy!"]

        self.lbl = ttk.Label(self.about_frame, wraplength='4i', justify=tk.LEFT, anchor=tk.N, text=''.join(self.text))
        self.lbl.pack(pady=10)

        # add to notebook (underline = index for short-cut character)
        self.nb.add(self.about_frame, text='Help', underline=0)

    def sort_list(self, listbox):
        """
        function to sort listbox items case insensitive
        """
        temp_list = []
        for items in listbox.get(0, tk.END):
            temp_list.append(str(items))
        temp_list.sort(key=str.lower)
        # delete contents of present listbox
        listbox.delete(0, tk.END)
        # load listbox with sorted data
        for item in temp_list:
            listbox.insert(tk.END, item)

    def host_game(self, event=None):
        try:
            all_kahoots_index = self.all_kahoots_listbox.curselection()
            my_kahoots_index = self.my_kahoots_listbox.curselection()

            if all_kahoots_index == ():  # requested game is in my_kahoots
                game_name = self.my_kahoots_listbox.get(int(my_kahoots_index[0]))
            else:  # requested game is in all_kahoots
                game_name = self.all_kahoots_listbox.get(int(all_kahoots_index[0]))

            self.controller.initialize_frame(WallClient, game_name=game_name)
            self.controller.show_frame(page_name="WallClient")
        except:
            pass

    def edit_game(self):
        pass

    def sign_out(self):
        """

        :return: function returns to the main screen
        """
        self.controller.show_frame(page_name="StartPage")
        self.controller.update_title('Welcome to Kahoot')
        self.controller.update_size(300, 200)
        self.controller.update()

    def close_server(self):
        self.controller.send_data(['close_server'])


class WallClient(tk.Frame):
    def __init__(self, parent, controller, game_name=None):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.parent = parent

        self.wait_on_recv = 100  # milliseconds
        # data control variables
        self.start_update = True
        self.game_update = True
        self.game_ended = False

        self.controller.socket.setblocking(0)
        self.controller.after(self.wait_on_recv, self.get_data)

        self.game_name = game_name
        self.current_question_number = 0
        self.controller.update_title(self.game_name)

        self.controller.send_data(['login', 'host_game', self.game_name])
        self.pin = None
        self.wait_for_players = None  # if false, waits for 30 seconds after one player is connected
        self.interval_between_questions = None  # if false wait 10 seconds before displaying the next question

        self.players_in_game = {}

    def get_data(self):
        if not self.game_ended:
            try:
                data = self.controller.socket.recv(self.controller.BUFSIZ)
                num = 0
                prev_index = 0
                tmp_data = ""
                for i in range(len(data)):
                    if data[i] == '[':
                        num += 1
                    elif data[i] == ']':
                        num -= 1
                    if num == 0:
                        if prev_index == 0:
                            tmp_data = data[:i+1]
                        else:
                            tmp_data = data[prev_index:i+1]
                        self.handle_data(eval(tmp_data))
                        prev_index = i + 1
            except Exception as e:
                if str(e) != '[Errno 10035] A non-blocking socket operation could not be completed immediately':
                    print e
            finally:
                self.controller.after(self.wait_on_recv, self.get_data)

    def handle_data(self, data):
        if type(data) != list:
            data = [data]
        if data[0] == 'server_down':
            self.controller.show_error('SERVER IS CLOSED', 'Server is now closed.')
            self.controller.show_frame(page_name="StartPage")
            self.controller.update_title('Welcome to Kahoot')
            self.controller.update_size(300, 200)
            self.controller.update()

        elif data[0] == 'error':
            self.controller.show_error('Game Error', data[1])
            self.controller.show_frame(page_name="StartPage")
            self.controller.update_title('Welcome to Kahoot')
            self.controller.update_size(300, 200)
            self.controller.update()

        elif data[0] == 'login' and data[1] == 'host_game':
            self.pin = data[2]
            self.wait_for_players = data[3]
            self.interval_between_questions = data[4]

            # create start screen and start getting updates from the server
            self.build_start_page()
            self.controller.show_frame(frame=self.frame)
            self.controller.send_data(['wall_display', 'start_update'])

        elif data[0] == 'wall_display':

            if data[1] == 'start_update':
                self.update_start_page(eval(data[2]))
                self.controller.show_frame(frame=self.frame)
                if self.start_update:
                    self.controller.send_data(['wall_display', 'start_update'])

            elif data[1] == 'game_update':

                if data[2] == 'first_question':
                    self.game_update = True
                    self.build_game_page(data[3], data[4:], self.wait_on_recv)
                    self.controller.send_data(['wall_display', 'game_update', 'game_update'])

                elif data[2] == 'game_update':
                    self.update_game_page(str(data[3]))
                    self.controller.update()
                    if self.game_update:
                        self.controller.send_data(['wall_display', 'game_update', 'game_update'])

                elif data[2] == 'round_results':
                    if not data[-1]:  # there is another question after this one
                        self.build_results_page(data[3])
                    else:
                        self.build_results_page(data[3], True)
                    self.controller.show_frame(frame=self.frame)

            elif data[1] == 'next_question':
                if data[3] != [None]:  # if there is a next question
                    self.game_update = True
                    self.build_game_page(data[2], data[3:], self.wait_on_recv)
                    self.controller.send_data(['wall_display', 'game_update', 'game_update'])

            elif data[1] == 'end_questionnaire':
                self.game_ended = True
                self.build_end_page(data[2])
                self.controller.update()

            else:  # unknown data
                pass

        else:  # unknown data
            pass

    def start_game(self):
        # check before starting a game
        if len(self.players_in_game) >= 2:  # at least two players are in the game
            self.start_update = False
            self.controller.send_data(['wall_display', 'game_update', 'first_question'])
        else:
            self.controller.show_error("Can't Start Game", "Not enough players connected\r\n(requires at least 2).", False)

    def build_start_page(self):
        '''

        :return: function builds a new game page
        '''
        self.frame = tk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nesw")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        self.frame.rowconfigure(2, weight=16)

        self.game_pin_label = ttk.Label(self.frame, text="Game Pin: %d" % self.pin)
        self.game_pin_label.grid(row=0, column=0, sticky="news", padx=10)

        self.num_of_players_label = ttk.Label(self.frame, text="0 Players")
        self.num_of_players_label.grid(row=1, column=0, sticky="news", padx=10)

        if self.wait_for_players:
            self.next_btn = ttk.Button(self.frame, text="Start", command=self.start_game)
            self.next_btn.grid(row=1, column=1, sticky="news", padx=10)
        else:
            self.timer_label = ttk.Label(self.frame, text="Game Begins in: ")
            self.timer_label.grid(row=1, column=1, sticky="news", padx=10)

        self.players_listbox = tk.Listbox(self.frame)
        self.players_listbox.grid(row=2, column=0, columnspan=2, sticky="senw", pady=10, padx=10)

    def update_start_page(self, players_in_game):
        self.players_in_game = players_in_game
        # update number of players in game
        self.num_of_players_label['text'] = str(len(players_in_game))+" Players"
        # clear the listbox
        self.players_listbox.delete(0, tk.END)
        # insert all names into the listbox
        for player in players_in_game:
            self.players_listbox.insert(tk.END, player)
        self.players_listbox.see(tk.END)

    def build_game_page(self, num_of_answers=0, info=None, after_waiting_time=0.1):
        '''

        :return: function builds a new game page
        '''
        self.num_of_answers = str(num_of_answers)

        # update question number
        self.current_question_number += 1
        self.current_question = info[0]
        self.current_correct_answers = {}  # saves the labels that are correct answers {label:T/F}

        if self.current_question:
            self.current_answers = info[1]
            self.correct_answers = info[2]
            # progress bar timing combined with root.after method (progress bar is not seconds)
            if int(info[3]) != 0:  # if after is zero, use exactly the supplied timing
                self.current_timer = int(info[3]) * 1000.0 / after_waiting_time
            else:
                self.current_timer = int(info[3])

            self.frame.grid_remove()  # hide previous frame
            self.frame = tk.Frame(self)
            self.frame.grid(row=0, column=0, sticky="nesw")

            self.frame.columnconfigure(0, weight=1)
            self.frame.rowconfigure(0, weight=1)
            self.frame.columnconfigure(1, weight=1)
            self.frame.rowconfigure(1, weight=1)
            self.frame.rowconfigure(2, weight=2)
            self.frame.rowconfigure(3, weight=3)

            self.game_question_label = ttk.Label(self.frame, text="Question number %s: %s"
                                                            % (str(self.current_question_number), self.current_question))
            self.game_question_label.grid(row=0, column=0, columnspan=2, sticky="news", padx=10)

            self.time_var = tk.Variable(self.frame)
            self.time_bar = ttk.Progressbar(self.frame, maximum=self.current_timer, variable=self.time_var)
            self.time_var.set(self.current_timer)
            self.time_bar.grid(row=1, column=0, sticky="news", padx=5)

            self.red_progress_bar = ttk.Style()
            self.red_progress_bar.theme_use("alt")
            self.red_progress_bar.configure("red.Horizontal.TProgressbar", foreground='red', background='red')

            self.green_progress_bar = ttk.Style()
            self.green_progress_bar.theme_use("alt")
            self.green_progress_bar.configure("green.Horizontal.TProgressbar", foreground='green', background='green')

            self.num_of_answers_label = ttk.Label(self.frame, text="Answers: %s" % self.num_of_answers)
            self.num_of_answers_label.grid(row=1, column=1, sticky="news", padx=5)

            # red answer
            if self.current_answers[0]:
                self.red_answer_label = tk.Label(self.frame, bg="red", fg="white", relief="groove",
                                                  activebackground="red", text=self.current_answers[0])
            else:
                self.red_answer_label = tk.Label(self.frame, bg="grey", relief="groove",
                                                  activebackground="grey")
            # blue answer
            if self.current_answers[1]:
                self.blue_answer_label = tk.Label(self.frame, bg="blue", fg="white", relief="groove",
                                                   activebackground="blue", text=self.current_answers[1])
            else:
                self.blue_answer_label = tk.Label(self.frame, bg="grey", relief="groove",
                                                   activebackground="grey")
            # green answer
            if self.current_answers[2]:
                self.green_answer_label = tk.Label(self.frame, bg="green", fg="white", relief="groove",
                                                    activebackground="green", text=self.current_answers[2])
            else:
                self.green_answer_label = tk.Label(self.frame, bg="grey", relief="groove",
                                                    activebackground="grey")
            # yellow answer
            if self.current_answers[3]:
                self.yellow_answer_label = tk.Label(self.frame, bg="yellow", fg="white", relief="groove",
                                                     activebackground="yellow", text=self.current_answers[3])
            else:
                self.yellow_answer_label = tk.Label(self.frame, bg="grey", relief="groove",
                                                     activebackground="grey")

            # initialize the correct answers
            for label in [self.red_answer_label, self.blue_answer_label, self.green_answer_label,
                          self.yellow_answer_label]:
                self.current_correct_answers[label] = False

            # match the label to its correct answer
            for answer in self.correct_answers:
                for label in [self.red_answer_label, self.blue_answer_label, self.green_answer_label,
                              self.yellow_answer_label]:
                    if label['text'] == answer:
                        self.current_correct_answers[label] = True

            self.red_answer_label.grid(row=2, column=0, sticky="news", pady=5, padx=5)
            self.blue_answer_label.grid(row=2, column=1, sticky="news", pady=5, padx=5)
            self.green_answer_label.grid(row=3, column=0, sticky="news", pady=5, padx=5)
            self.yellow_answer_label.grid(row=3, column=1, sticky="news", pady=5, padx=5)

        self.frame.update()
        self.update()

    def update_game_page(self, players_answers):
        """

        :param players_answers: num of answers (int)
        :param next_btn: display the 'next' button if time is up
        :return: self.red_answer_label.grid(row=2, column=0, sticky="news", pady=5, padx=5)
        """
        # update num of players
        self.num_of_answers_label['text'] = "Answers: %s" % players_answers
        # update progress bar
        self.time_var.set(self.time_var.get() - 1)
        # turn the progress bar red if not much time is left
        if self.time_var.get() <= self.current_timer/2.5:
            self.time_bar['style'] = "red.Horizontal.TProgressbar"
        else:
            self.time_bar['style'] = "green.Horizontal.TProgressbar"
        self.update()

        # check if time is up
        if self.time_var.get() <= 0:  # time is up, get results and update the gui
            self.game_update = False
            # show correct answer/s
            self.show_correct_answer()
            # remove the 'Answers Button'
            self.num_of_answers_label.grid_remove()
            # update the button
            self.next_btn = ttk.Button(self.frame, text="Next", command=self.create_score_board)
            self.next_btn.grid(row=1, column=1, sticky="news", padx=5)  # on top of the number of answers label
            self.controller.update()
        else:  # keep getting updates about the number of answers
            self.game_update = True

    def show_correct_answer(self):
        for label in self.current_correct_answers:
            if not self.current_correct_answers[label]:  # label holds an incorrect answer
                # color out incorrect answers
                label['bg'] = "grey"
            else:
                label['bg'] = "dark green"

    def create_score_board(self):
        self.controller.send_data(['wall_display', 'game_update', 'round_results'])

    def build_results_page(self, results, last_round_results=False):

        self.frame.grid_remove()  # hide previous frame
        self.frame = tk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nesw")

        # Create results table
        result_tree_view = ttk.Treeview(self.frame)
        result_tree_view['columns'] = ('Place', 'Player', 'Score')
        result_tree_view.heading('#0', text='Place')
        result_tree_view.column('#0', anchor='center', width=60)
        result_tree_view.heading('#1', text='Player')
        result_tree_view.column('#1', anchor='center', width=60)
        result_tree_view.heading('#2', text='Score')
        result_tree_view.column('#2', anchor='center', width=60)
        result_tree_view_scrollbar = ttk.Scrollbar(self.frame)
        result_tree_view_scrollbar.pack(side="right", fill="y")
        result_tree_view.config(yscrollcommand=result_tree_view_scrollbar.set)
        result_tree_view_scrollbar.config(command=result_tree_view.yview)
        result_tree_view.pack(side="top", expand=True, fill="both")

        # insert players and scores into results table
        for i in range(0, len(results)):
            result_tree_view.insert('', 'end', text="%d" % (i + 1), values=(results[i][0], results[i][1]))

        if last_round_results:
            continue_btn = ttk.Button(self.frame, text='Continue', command=self.get_final_results)
        else:
            continue_btn = ttk.Button(self.frame, text='Continue', command=self.get_next_question)
        continue_btn.pack(expand=True, fill="both")

        self.frame.update()
        self.update()

    def get_final_results(self):
        self.controller.send_data(['wall_display', 'end_questionnaire'])

    def get_next_question(self):
        self.controller.send_data(['wall_display', 'next_question'])

    def build_end_page(self, winners):

        self.frame.grid_remove()  # hide previous frame
        self.frame = tk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nesw")

        # Create results table
        result_tree_view = ttk.Treeview(self.frame)
        result_tree_view['columns'] = ('Place', 'Player', 'Score', 'Number of Correct Answers')
        result_tree_view.heading('#0', text='Place')
        result_tree_view.column('#0', anchor='center', width=60)
        result_tree_view.heading('#1', text='Player')
        result_tree_view.column('#1', anchor='center', width=60)
        result_tree_view.heading('#2', text='Score')
        result_tree_view.column('#2', anchor='center', width=60)
        result_tree_view.heading('#3', text='Number of Correct Answers')
        result_tree_view.column('#3', anchor='center', width=60)
        result_tree_view_scrollbar = ttk.Scrollbar(self.frame)
        result_tree_view_scrollbar.pack(side="right", fill="y")
        result_tree_view.config(yscrollcommand=result_tree_view_scrollbar.set)
        result_tree_view_scrollbar.config(command=result_tree_view.yview)
        result_tree_view.pack(side="top", expand=True, fill="both")

        # insert players and scores into results table
        for i in range(0, len(winners)):
            result_tree_view.insert('', 'end', text="%d" % (i + 1), values=(winners[i][0], winners[i][1], winners[i][2]))

        finish_btn = ttk.Button(self.frame, text='Finish', command=lambda: self.controller.handle_frame("UserHomePage"))
        finish_btn.pack()

        self.frame.update()
        self.update()


class GameTemplate(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        '''First Half of the template'''

        self.frame = tk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nesw")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.questionnaire_label = ttk.Label(self.frame, text='Questionnaire Name:')
        self.questionnaire_label.grid(row=0, column=0, columnspan=2, sticky="news")

        self.question_listbox = tk.Listbox(self.frame)
        self.question_listbox.grid(row=1, column=0, rowspan=3, columnspan=2, sticky="news")

        self.add_question_btn = ttk.Button(self.frame, text='Add Question')
        self.add_question_btn.grid(row=4, column=0, sticky="news")

        self.save_questionnaire_btn = ttk.Button(self.frame, text='Save Questionnaire')
        self.save_questionnaire_btn.grid(row=4, column=1, sticky="news")

        '''Second Half of the template'''

        self._frame = tk.Frame(self)
        self._frame.grid(row=0, column=2, sticky="nesw")
        self._frame.columnconfigure(0, weight=1)
        self._frame.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.questionnaire_name_entry = ttk.Entry(self._frame)
        self.questionnaire_name_entry.grid(row=0, column=0, columnspan=2, sticky="news")

        self.question_label = ttk.Label(self._frame, text='Something')
        self.question_label.grid(row=1, column=0, columnspan=2, sticky="news")

        '''Answers Frame (inside the second half of the template)'''
        self.answers_frame = tk.Frame(self._frame)
        self.answers_frame.grid(row=2, column=0, sticky="nesw")
        self.answers_frame.columnconfigure(0, weight=1)
        self.answers_frame.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.one = ttk.Label(self.answers_frame, text="1.")
        self.two = ttk.Label(self.answers_frame, text="2.")
        self.three = ttk.Label(self.answers_frame, text="3.")
        self.four = ttk.Label(self.answers_frame, text="4.")
        self.one.grid(row=0, column=0, sticky="news")
        self.two.grid(row=1, column=0, sticky="news")
        self.three.grid(row=2, column=0, sticky="news")
        self.four.grid(row=3, column=0, sticky="news")

        self.answer_one = ttk.Entry(self.answers_frame)
        self.answer_two = ttk.Entry(self.answers_frame)
        self.answer_three = ttk.Entry(self.answers_frame)
        self.answer_four = ttk.Entry(self.answers_frame)
        self.answer_one.grid(row=0, column=1, columnspan=2, sticky="news")
        self.answer_two.grid(row=1, column=1, columnspan=2, sticky="news")
        self.answer_three.grid(row=2, column=1, columnspan=2, sticky="news")
        self.answer_four.grid(row=3, column=1, columnspan=2, sticky="news")

        self.first_chk_btn_var = tk.BooleanVar(self.answers_frame)
        self.first_answer_chk_btn = tk.Checkbutton(self.answers_frame, fg='darkgreen', relief=tk.FLAT, variable=self.first_chk_btn_var)
        self.second_chk_btn_var = tk.BooleanVar(self.answers_frame)
        self.second_answer_chk_btn = tk.Checkbutton(self.answers_frame, fg='darkgreen', relief=tk.FLAT, variable=self.second_chk_btn_var)
        self.third_chk_btn_var = tk.BooleanVar(self.answers_frame)
        self.third_answer_chk_btn = tk.Checkbutton(self.answers_frame, fg='darkgreen', relief=tk.FLAT, variable=self.third_chk_btn_var)
        self.fourth_chk_btn_var = tk.BooleanVar(self.answers_frame)
        self.fourth_answer_chk_btn = tk.Checkbutton(self.answers_frame, fg='darkgreen', relief=tk.FLAT, variable=self.fourth_chk_btn_var)
        self.first_answer_chk_btn.grid(row=0, column=3, sticky="news")
        self.second_answer_chk_btn.grid(row=1, column=3, sticky="news")
        self.third_answer_chk_btn.grid(row=2, column=3, sticky="news")
        self.fourth_answer_chk_btn.grid(row=3, column=3, sticky="news")


if __name__ == '__main__':
    app = GameClient()
    app.mainloop()
