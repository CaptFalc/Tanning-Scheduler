######################################
# Skeleton: Ben Lawson <balawson@bu.edu>
# Edited by: Addison Baum <atomsk@bu.edu> Wadi Ahmed Brayan Pichardo
######################################
# Some code adapted from
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, request, render_template
from flaskext.mysql import MySQL
import flask_login
from dotenv import load_dotenv
import os
import requests

load_dotenv()
mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

# These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = os.environ.get("tanningpassword")
app.config['MYSQL_DATABASE_DB'] = 'tanningscheduler'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

# begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()


def getUvi(lat, lon, exclude="minutely,current,alerts"):
	#Takes coordinates (ints), returns tuple of two lists: uv index of next 48 hours and 5 days.
    apikey = os.environ.get('apikey')
    api_url = "https://api.openweathermap.org/data/3.0/onecall?lat={0}&lon={1}&exclude={2}&appid={3}".format(lat, lon, exclude, apikey)
    response=requests.get(api_url)
    response=response.json()
    hours=[]
    days=[]
    for x in response["hourly"]:
        dt=x["dt"]
        uvi=x["uvi"]
        hours.append(dt,uvi)     
    print("daily")
    for x in range(5):
        y=response["daily"][x]
        dt=y["dt"]
        uvi=y["uvi"]
        days.append((dt,uvi))
    return (hours,days)

def getLocation(user):
	#Gets location of user from database, if not found returns False
	cursor=conn.cursor()
	if cursor.execute("SELECT zipcode FROM Users where email='{0}'".format(user)):
		return cursor.fetchone()
	else:
		return False


#Starter code for finding schedule. Takes user, uv preferences, schedule, outputs uv schedule data
def getSchedule(user,preferences,schedule=None):
    location=getLocation(user)
    return 0
'''
	if location:
		cursor=conn.cursor()
		cursor.execute("SELECT email from Users ")
	else:
		return False 
'''

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users")
	return cursor.fetchall()

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
#end login code	

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user


@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0])
	user.is_authenticated = request.form['password'] == pwd
	return user


'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''


@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	# The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	# check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0])
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user)  # okay login in user
			# protected is a function defined in this file
			return flask.redirect(flask.url_for('protected'))

	# information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"


@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out')


@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')

# you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier


@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', supress='True')


@app.route("/register", methods=['POST'])
def register_user():
	try:
		email=request.form.get('email')
		name=request.form.get('name')
		password=request.form.get('password')
		zipcode=request.form.get('zipcode')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print(cursor.execute("INSERT INTO Users (email, name, password, zipcode) VALUES (%s, %s,%s,%s)",(email, name, password,zipcode)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('register'))



# default page


@app.route("/", methods=['GET'])
def hello():
	return render_template('hello.html')

@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('hello.html', name=flask_login.current_user.id,message="Here's your profile")


@app.route("/scheduler", methods=['POST'])
@flask_login.login_required
def calendar():
	#gets user inputs, redirects to page with schedule
	try:
		preferences=request.form.get('preferences')	
		schedule=request.form.get('schedule')
		user=flask_login.current_user
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
	schedule=getSchedule(user,preferences,schedule)
	if(schedule):
		pass
	else:
		print("Error")

if __name__ == "__main__":
	# this is invoked when in the shell  you run
	# $ python app.py
	app.run(port=5000, debug=True)
	