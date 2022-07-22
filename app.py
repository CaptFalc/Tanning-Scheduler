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
from icalendar import Calendar, Event
from datetime import datetime
from pathlib import Path
import flask_login
from dotenv import load_dotenv
import os
import requests
import pgeocode
import pytz

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
    # Takes coordinates (ints), returns tuple of two lists: uv index of next 48 hours and 5 days.
    apikey = os.environ.get('apikey')
    api_url = "https://api.openweathermap.org/data/3.0/onecall?lat={0}&lon={1}&exclude={2}&appid={3}".format(
        lat, lon, exclude, apikey)
    response = requests.get(api_url)
    response = response.json()
    hours = []
    days = []
    for x in response["hourly"]:
        dt = x["dt"]
        uvi = x["uvi"]
        hours.append((dt, uvi))
    for x in range(5):
        y = response["daily"][x]
        dt = y["dt"]
        uvi = y["uvi"]
        days.append((dt, uvi))
    return (hours, days)

#uvi: [(unixtime,uvindex)]


def processUvi(uvidata,offset):
    colors = {
        0: "black",
        1:"green",
        2:"green",
        3:"yellow",
        4:"yellow",
        5:"yellow",
        6:"orange",
        7:"orange",
        8:"red",
        9:"red",
        10:"red",
        11:"purple"
    }
    hours = []
    days = []
    numofDays = 1
    nightTime = False
    for hour in uvidata[0]:
        color = colors[int(hour[1])]
        time = datetime.utcfromtimestamp(hour[0]).strftime('%H%M')
        time = int(time)
        time = (time + (offset * 100)) % 2400
        endtime = (int(time) + 100) % 2400
        if time >= 1800 and nightTime is False:
            numofDays += 1
            nightTime = True
        elif time >= 1800:
            nightTime = True
        else:
            nightTime = False
        if time >= 700 and time <= 1800 and endtime <= 1800:
            hours.append((time, endtime, numofDays, color))
    i = 1
    for day in uvidata[1]:
        color = colors[int(day[1])]
        days.append((i, color))
        i += 1
    return (hours,days)

def processSchedule(schedule):
	opencal = open(schedule, 'rb')
	cal = Calendar.from_ical(opencal.read())
	event=[]
	for component in cal.walk():
		if component.name == "VEVENT":
			start = component.decoded("dtstart").timestamp()
			end = component.decoded("dtend").timestamp()
			event.append((start,end))
	return event

def parseCal(uvi,schedule=None):
	'''
	Takes: uvi: two lists, hours and days. Hours contains tuples of (starttime,endtime,day,color), days contains tuples of (day,color) 
	'''
	tags=""
	hours=uvi[0]
	days=uvi[1]
	session=0
	starttime=0
	endtime=0
	#Process days
	for x in days:
		day=x[0]
		color=x[1]
		tags+='''<div class="session session-{0} background-color:{1};track-{2}" style="grid-column: track-{2}; grid-row: time-0700 / time-1800;">
    <h3 class="session-title"><a href="#">Talk Title</a></h3>
    <span class="session-time"></span>
    <span class="session-presenter"></span>
  </div>'''.format(session,color,day)
		session+=1
	for x in hours:
		starttime=x[0]
		endtime=x[1]
		day=x[2]
		color=x[3]
		tags+='''<div class="session session-{0} background-color:{1};track-{2}" style="grid-column: track-{2}; grid-row: time-{3} / time-{4};">
    <h3 class="session-title"><a href="#">Talk Title</a></h3>
    <span class="session-time"></span>
    <span class="session-presenter"></span>
  </div>'''.format(session,color,day,starttime,endtime)
		session+=1
	if schedule:
		formatted=processSchedule(schedule)
		#Gives tuples of (starttime,endtime,day)
		for x in formatted:
			tags+='''<div class="session session-{0} background-color:gray;track-{1}" style="grid-column: track-{1}; grid-row: time-{2} / time-{3};">
    <h3 class="session-title"><a href="#">Talk Title</a></h3>
    <span class="session-time"></span>
    <span class="session-presenter"></span>
  </div>'''.format(session,day,starttime,endtime)
			session+=1
	return tags
		

	



def getUserzip(useremail):
	cursor = conn.cursor()
	cursor.execute(
            "Select zipcode from users where email='{0}'".format(useremail))
	zipcode=cursor.fetchone()
	return zipcode[0]

def getLocation(useremail):
    # Gets location of user from database, if not found returns False
    cursor = conn.cursor()
    if cursor.execute("SELECT lat,lon from zipcodes where zipcode in(select zipcode from users where email='{0}')".format(useremail)):
        return cursor.fetchone()
    else:
        zipcode =getUserzip(useremail)
        latlon = getlatLon(zipcode)
        cursor.execute("Insert INTO zipcodes (zipcode,lat,lon) VALUES (%s,%s,%s)",
                       zipcode, latlon[0], latlon[1])
        conn.commit()
        return latlon




'''
	if location:
		cursor=conn.cursor()
		cursor.execute("SELECT email from Users ")
	else:
		return False 
'''
def getOffset(lat,lon):
    key=str(os.environ.get('timezonekey'))  
    url="http://api.timezonedb.com/v2.1/get-time-zone?key={0}&format=json&by=position&lat={1}&lng={2}".format(
        key,lat,lon
    )
    response=requests.get(url)
    response=response.json()
    offset=int(response["gmtOffset"])
    offset=offset/3600
    return offset
	

def updateZip(email,zipcode):
	cursor=conn.cursor()
	cursor.execute("UPDATE users SET zipcode='{0}' WHERE email='{1}'".format(
		zipcode,email
	))


def getUserList():
    cursor = conn.cursor()
    cursor.execute("SELECT email from Users")
    return cursor.fetchall()


def isEmailUnique(email):
    # use this to check if a email has already been registered
    cursor = conn.cursor()
    if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
        # this means there are greater than zero entries with that email
        return False
    else:
        return True


def getlatLon(zip):
    country = pgeocode.Nominatim('us')
    query = country.query_postal_code(zip)
    latlon = (query["latitude"], query["longitude"])
    return latlon


# end login code

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
    cursor.execute(
        "SELECT password FROM Users WHERE email = '{0}'".format(email))
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
        return render_template('login.html')
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
            getUserzip(email)
            return render_template("layout.html",zipcode=getUserzip(email))

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
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        zipcode = request.form.get('zipcode')
        print(zipcode)
    except:
        # this prints to shell, end users will not see this (all print statements go to shell)
        print("couldn't find all tokens")
        return flask.redirect(flask.url_for('register'))
    cursor = conn.cursor()
    test = isEmailUnique(email)
    if test:
        print(cursor.execute("INSERT INTO Users (email, name, password, zipcode) VALUES (%s, %s,%s,%s)",
              (email, name, password, zipcode)))
        conn.commit()
        # log user in
        user = User()
        user.id = email
        flask_login.login_user(user)
        return render_template('hello.html', name=email, message='Account Created!')
    else:
        print("couldn't find all tokens")
        return flask.redirect(flask.url_for('register'))

@app.route("/layout", methods=['GET'])
@flask_login.login_required
def layoutPage():
    useremail = flask_login.current_user.id
    zipcode=getUserzip(useremail)
    return render_template('layout.html', zipcode=zipcode)


# default page


@app.route("/", methods=['GET'])
def hello():
    return render_template('hello.html')

@app.route("/calendar", methods=['GET'])
def welcome():
    return render_template("calendar.html")

@app.route("/calendar", methods=['POST'])
@flask_login.login_required
def calendar():
   # gets user inputs, redirects to page with schedule
	try:
		schedule = request.form.get('schedule')
		useremail = flask_login.current_user.id
		location=getLocation(useremail)
		uvi=getUvi(location[0],location[1])
		parseCal(uvi,schedule)
	except:
		# this prints to shell, end users will not see this (all print statements go to shell)
		useremail = flask_login.current_user.id
		location=getLocation(useremail)
		uvi=getUvi(location[0],location[1])
		schedule=parseCal(uvi)
	return 0



@app.route("/updatezipcode", methods=['POST'])
@flask_login.login_required
def changezip():
	zipcode= request.form.get('zipcode')
	useremail = flask_login.current_user.id
	updateZip(useremail,zipcode)
	return render_template('layout.html', zipcode=zipcode)


if __name__ == "__main__":
    # this is invoked when in the shell  you run
    # $ python app.py
    app.run(port=5000, debug=True)
