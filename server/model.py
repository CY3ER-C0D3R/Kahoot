import sqlite3 as lite
import datetime


class Module(object):
    def __init__(self):
        self.create_kahoot_db_tables()

    @staticmethod
    def connect_to_database(file_name="Kahoot.sqlite"):
        """

        :param file_name: string
        :return: connects to db
        """
        conn = None

        try:
            conn = lite.connect(file_name)
        except lite.Error, e:
            print e
        finally:
            return conn

    def create_kahoot_db_tables(self):
        """

        :return: function creates the kahoot database tables
        """
        conn = self.connect_to_database()

        # conn.execute('''DROP TABLE USERS''')
        # conn.execute('''DROP TABLE QUESTIONNAIRES''')
        # conn.execute('''DROP TABLE HISTORY''')

        try:
            # USERS Table
            create_str = '''CREATE TABLE USERS (
                    USERNAME TEXT PRIMARY KEY NOT NULL,
                    PASSWORD TEXT NOT NULL
                    )'''
            conn.execute(create_str)
            conn.commit()  # save changes
        except lite.Error, e:
            if str(e) != 'table USERS already exists':
                print e
        try:
            # QUESTIONNAIRES Table
            create_str = '''CREATE TABLE QUESTIONNAIRES (
                    PUBLISHER TEXT NOT NULL,
                    NUMBER_AND_NAME TEXT PRIMARY KEY NOT NULL,
                    QUESTIONS_AND_ANSWERS TEXT NOT NULL,
                    QUESTION_NUMBERS_AND_TIMES TEXT NOT NULL,
                    AUTOMATIC_TIMING_SETTINGS TEXT NOT NULL,
                    LAST_UPDATED TEXT,
                    PLAYERS TEXT
                    )'''
            conn.execute(create_str)
            conn.commit()  # save changes
        except lite.Error, e:
            if str(e) != 'table QUESTIONNAIRES already exists':
                print e
        finally:
            try:
                # HISTORY Table
                create_str = '''CREATE TABLE HISTORY (
                            PUBLISHER TEXT NOT NULL,
                            GAME_NAME TEXT PRIMARY KEY NOT NULL,
                            NUM INT NOT NULL,
                            LAST_PLAYED TEXT
                            )'''
                conn.execute(create_str)
                conn.commit()  # save changes
            except lite.Error, e:
                if str(e) != 'table HISTORY already exists':
                    print e

    def add_user(self, username, password):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        if conn:
            try:
                cursor.execute('''INSERT INTO USERS(username, password) VALUES(?,?)''', (username, password))
                conn.commit()
                return 'user added successfully'
            except lite.IntegrityError as e:
                if str(e) == 'column USERNAME is not unique':
                    return 'Username is already in use. '

    def get_user_password(self, username):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        if conn:
            cursor.execute('''SELECT password FROM USERS WHERE username=?''', (username,))
            result = cursor.fetchone()
            conn.close()
            if result:  # username was found in database
                return result[0]  # return matching password
            return result  # None

    def add_new_questionnaire(self, publisher, questionnaire_name, questions_and_answers, correct_answers_and_times,
                              automatic_timing_settings):
        # check if questionnaire name is unique
        conn = self.connect_to_database()
        cursor = conn.cursor()

        if conn:
            cursor.execute('''SELECT game_name FROM HISTORY''')
            result = cursor.fetchall()
            if result:
                result = result[0]
            if not result or questionnaire_name not in result:  # the game doesn't exist in the database
                self.add_questionnaire(publisher, questionnaire_name, questions_and_answers, correct_answers_and_times,
                                       automatic_timing_settings)
                return True
            else:
                return False  # action couldn't be completed because questionnaire_name is not unique

    def add_questionnaire(self, publisher, questionnaire_name, questions_and_answers, correct_answers_and_times,
                          automatic_timing_settings, players=None):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        if not players:  # only add last_updated if no players are in the game
            time = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
        else:  # adding a played game
            time = self.get_all_info(questionnaire_name)[0][-2]  # don't change the last_updated time since it refers to when was the game last edited

        self.add_to_history(publisher, questionnaire_name)
        questionnaire_number = self.get_from_history(questionnaire_name)[0]  # number of times played

        if conn:
            cursor.execute('''INSERT INTO QUESTIONNAIRES(publisher, number_and_name, questions_and_answers, question_numbers_and_times,
            automatic_timing_settings, last_updated, players) VALUES(?,?,?,?,?,?,?)''',
                           (publisher, str(questionnaire_number)+" "+questionnaire_name, questions_and_answers,
                            correct_answers_and_times, automatic_timing_settings, time, players))
            conn.commit()

    def add_to_history(self, publisher, game_name):
        """

        :param game_name: string
        :return: function updates the number of times a game has been played and adds a new game history if doesn't exist
        """
        num = self.get_from_history(game_name)[0]

        current_time = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M:%S")

        conn = self.connect_to_database()
        cursor = conn.cursor()

        if conn:
            if num:  # game was already in history, update num
                num += 1
                cursor.execute("""UPDATE HISTORY SET num=?, last_played=? WHERE game_name=?""",
                               (num, current_time, game_name))
            else:  # first time played
                cursor.execute('''INSERT INTO HISTORY(publisher, game_name, num, last_played) VALUES(?,?,?,?)''',
                               (publisher, game_name, 1, current_time))
            conn.commit()

    def get_from_history(self, game_name):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        if conn:
            cursor.execute('''SELECT num, last_played FROM HISTORY
            WHERE game_name=?''', (game_name,))
            result = cursor.fetchall()
            conn.close()
            if not result:  # empty list
                return None,
            return result[0]  # tuple of (num, last_updated)

    def update_password(self, username, new_password):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        if conn:
            cursor.execute("""UPDATE USERS SET password=? WHERE username=?""", (new_password, username))
            conn.commit()

    def update_questions_and_answers(self, questionnaire_name, questions_and_answers, question_numbers_and_times):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        questionnaire_number = self.get_from_history(questionnaire_name)[0]
        questionnaire = str(questionnaire_number)+" "+questionnaire_name
        time = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M:%S")

        if conn and question_numbers_and_times and questions_and_answers:
            cursor.execute("""UPDATE QUESTIONNAIRES SET questions_and_answers=?, question_numbers_and_times=?,
            last_updated=? WHERE number_and_name=?""",
                           (questions_and_answers, question_numbers_and_times, time, questionnaire))
            conn.commit()

    def update_players_and_scores(self, questionnaire_name, players_and_scores):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        questionnaire_number = self.get_from_history(questionnaire_name)[0]
        time = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M:%S")

        if conn:
            cursor.execute("""UPDATE QUESTIONNAIRES SET players=?, last_updated=? WHERE number_and_name=?""",
                           (players_and_scores, time, str(questionnaire_number)+" "+questionnaire_name))
            conn.commit()

    def get_questions_and_answers(self, questionnaire_name):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        questionnaire_number = self.get_from_history(questionnaire_name)[0]

        if conn:
            cursor.execute('''SELECT questions_and_answers, question_numbers_and_times FROM QUESTIONNAIRES
            WHERE number_and_name=?''', (str(questionnaire_number)+" "+questionnaire_name,))
            result = cursor.fetchall()
            conn.close()
            if result:
                return result[0]  # tuple of (questions_and_answers, question_numbers_and_times)
            return None

    def get_time_settings(self, questionnaire_name):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        questionnaire_number = self.get_from_history(questionnaire_name)[0]

        if conn:
            cursor.execute('''SELECT automatic_timing_settings FROM QUESTIONNAIRES
            WHERE number_and_name=?''', (str(questionnaire_number)+" "+questionnaire_name,))
            result = cursor.fetchall()
            conn.close()
            return result[0][0]  # dictionary of time settings

    def get_all_info(self, questionnaire_name):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        all_data = []

        questionnaire_number = self.get_from_history(questionnaire_name)[0]

        if conn:
            for i in range(1, questionnaire_number+1):
                cursor.execute('''SELECT * FROM QUESTIONNAIRES
                WHERE number_and_name=?''', (str(questionnaire_number)+" "+questionnaire_name,))
                result = cursor.fetchall()
                data = list(result[0])
                all_data.append(data)
            all_data.append(self.get_from_history(questionnaire_name))  # more info about the questionnaire
            conn.close()
            return all_data  # list of lists of database data

    def get_all_questionnaries(self):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        questionnaires = []

        if conn:
            cursor.execute('''SELECT game_name FROM HISTORY''')
            result = cursor.fetchall()
            for questionnaire in result:
                questionnaires += list(questionnaire)
            conn.close()
            return questionnaires

    def get_user_questionnaires(self, username):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        user_questionnaries = []

        if conn:
            cursor.execute('''SELECT game_name FROM HISTORY WHERE publisher=?''', (username,))
            result = cursor.fetchall()
            for questionnaire in result:
                user_questionnaries += list(questionnaire)
            conn.close()
            return user_questionnaries


'''
module_object = Module()

module_object.add_questionnaire('admin', 'test1', "{'some question':[('Answer1',True),('Answer2',False)]}",
                                "{'some question':(1,30)}","{'wait_for_players':True, 'interval':True}")
module_object.add_user('admin', 'aaa')
module_object.update_password('admin', 'bbb')
module_object.update_questions_and_answers('test1',
                                           "{'some question after changed':[('Answer1',True),('Answer2',False)]}",
                                           "{'some question after changed':(1,30)}")
module_object.update_players_and_scores('test1', 'yuval:100, roon:95')

module_object.add_questionnaire('admin', 'test2', "{'some new question':[('Answer1',True),('Answer2',False)]}",
                                "{'some new question':(1,30)}","{'wait_for_players':True, 'interval':True}")
module_object.add_questionnaire('some user', 'test3', "{'some new question':[('Answer1',True),('Answer2',False)]}",
                                "{'some new question':(1,30)}","{'wait_for_players':True, 'interval':True}")

#print module_object.get_all_info('test1')[1]
#print module_object.get_all_info('test1')[0][-3]

print module_object.get_all_questionnaries()
print module_object.get_user_questionnaires('Yuval')
print eval(module_object.get_time_settings('test1'))['interval']
'''

# ================================================== ADMIN CREATED GAMES ============================================ #
'''
module_object = Module()
module_object.add_user('admin', 'admin')
module_object.add_user('yuval', 'aaa')
module_object.add_new_questionnaire('admin', 'Technology',
                                    "{'What is the maximum number of people in a WhatsApp group?':[('88',False), ('100',False), ('256',True), ('216',False)],"
                                    "'On which logo does a paper plane appear?':[('Bezeq',False), ('Telegram',True), ('IBM',False), ('Pango', False)],"
                                    "'What is the color of the letter L on the google logo?':[('Red',False), ('Blue',False), ('Green',True), ('Yellow', False)],"
                                    "'What is the name of the founder of Wikipedia?':[('Yitzhak Shamir',False), ('Jimmy Wales',True), ('Bruce Springsteen',False), ('Charles Babbage',False)],"
                                    "'TeX is':[('A typesetting system',True),('A high level programming language',False),('A text editor',False),('A Html/CSS editor',False)]}",
                                    "{'What is the maximum number of people in a WhatsApp group?':(1,10),"
                                    "'On which logo does a paper plane appear?':(2,10),"
                                    "'What is the color of the letter L on the google logo?':(3,10),"
                                    "'What is the name of the founder of Wikipedia?':(4,10),"
                                    "'TeX is':(5,10)}",
                                    "{'wait_for_players':True, 'interval':True}")

module_object.add_new_questionnaire('yuval', 'Flags and Countries',
                                    "{'What is the only country that her flag is not a square?':[('Nepal',True), ('China',False), ('France',False), ('Israel',False)],"
                                    "'How many starts are in the flag of china?':[('5',True), ('6',False), ('4',False), ('1', False)],"
                                    "'What colors appear on the flag of Austria?':[('Red and Blue',False), ('Green and Red',False), ('Red and white',True), ('Yellow and Blue', False)],"
                                    "'What is the official language in Greenland?':[('English',False), ('Greenlandic',True), ('French',False), ('German',False)],"
                                    "'Lombardy is a district in':[('Switzerland',False),('Italy',True),('Spain',False),('France',False)]}",
                                    "{'What is the only country that her flag is not a square?':(1,15),"
                                    "'How many starts are in the flag of china?':(2,7),"
                                    "'What colors appear on the flag of Austria?':(3,10),"
                                    "'What is the official language in Greenland?':(4,8),"
                                    "'Lombardy is a district in':(5,12)}",
                                    "{'wait_for_players':True, 'interval':True}")
'''


