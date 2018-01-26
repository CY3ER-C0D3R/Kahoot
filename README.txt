INFORMATION ABOUT THE GAME:
======================
The game starts with a three-choice opening screen. The user can either 'log-in' (in order to host a game), 
'sign-up' in order to create a new user, or 'Join-a-Game' in order to enter a game. 
If the user decides to 'sign-up' he will be required to enter a username and password which will then be sent 
to the server and stored in the database (if user does not exist in the db).
If the user decides to 'log-in' and enters the correct username and password, his user home page will appear accordingly. 
This screen consists of his kahoots, all the kahoots made and some basic help info. 
The user can pick one of the buttons on the side, and in particular can press 'Start a Game' in order to host a game. 
If the user is the admin, he will get another option – 'Close Server' which will close the server, and end all the running games.
If the user decides to 'Join-a-Game', he will be required to enter the game pin and game name, and if validated (server return True),
 the client will be required to pick a game name. All information is updated in the server and the wall-client immediately. 
Each game has questions and timing which are transferred from the server (database) to the wall client and from the wall client 
back to the server and finally to the other player (game clients). Updating is according to 'after' method time, 
specifically every 100 milliseconds. 
At the end of each round, the results are displayed in the wall client, and at the end of the game all players receive their 
place and points.
The game is saved if it ends with more than one player and all the questions were passed. 
The game may end if the admin decides to close the server and an according message will be displayed to the clients. 
Client displays won't close automatically but all functions on the start page will not be available and will return an error message.


INFORMATION ABOUT THE PROGRAM:
========================
The program is written in an MVC way. The server has a module (the db) and a controller (mainly the select method). 
The client's controller and view are combined as part of the Tkinter functionality. 



