from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_caching import Cache
from flask import session as flaskSession
import requests
import uuid
from skyfield.api import load, Topos, load_constellation_map, Star, load_constellation_names
from datetime import datetime, timezone
from passwordchecker import PasswordChecker
from setup_db import User
from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

# Configure Flask Caching
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
cache = Cache(app)

#Secret key for session management
app.secret_key = str(uuid.uuid4())

#Database setup
engine = create_engine('sqlite:///userdata.db')
Session = sessionmaker(bind=engine)
sessionDb = Session()

#Dashboard
@app.route("/")
def home():
    flaskSession['location'] = None
    flaskSession['time'] = datetime.now()
    formatted_time = flaskSession['time'].strftime("%I:%M %p, %A %d %B %Y")

    loggedIn = False
    userId = flaskSession.get('userId')
    if userId:
        loggedIn = True

    return render_template("index.html", location=flaskSession['location'], time=formatted_time, loggedIn=loggedIn, username=flaskSession.get('username'))

#Signup/login pages
@app.route("/signup", methods=["GET"])
def signup():
    return render_template("signup.html")

@app.route("/signup", methods=["POST"])
def sibmitSignup():
    # Get the form data
    username = request.form['username']
    password = request.form['password']
    password_confirm = request.form['confirm-password']
    errors = []

    # Check for errors in the form data
    if username == '' or password == '' or password_confirm == '':
        errors.append('empty_field')
    elif len(password) < 8:
        errors.append('password_length')
    
    if password != password_confirm:
        errors.append('match_password')
    
    feedback = scorePassword(password)
    print(feedback)
    if feedback[0] < 60:
        errors.append('password_security')


    users = sessionDb.query(User).filter(User.username == username).all()
    if len(users) > 0:
        errors.append('username_taken')

    

    if len(errors) > 0:
        return render_template('signup.html', errors=errors, password_feedback=feedback[1], password_score=feedback[0])
    else:
        unique_id = str(uuid.uuid4())#gives each user a unique uuid

        user = User(id=unique_id, username=username, password=generate_password_hash(password))
        sessionDb.add(user)
        sessionDb.commit()
        
        flaskSession['userId'] = user.id
        flaskSession['username'] = user.username
        return redirect(url_for('home'))


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def submitLogin():
    # Get the form data
    username = request.form['username']
    password = request.form['password']

    # Check if the form data is empty
    if username == '' or password == '':
        #usernameFailed and passwordFailed are used to keep the form data in the input fields between failed login attempts
        return render_template("login.html",failed_attempt=True,usernameFailed=username,passwordFailed=password)

    # Check if the user exists
    user = sessionDb.query(User).filter(User.username == username).first()
    if user and user.check_password(password):
        # Set the session variables
        flaskSession['userId'] = user.id
        flaskSession['username'] = user.username
        return redirect(url_for('home'))
    else:
        return render_template("login.html",failed_attempt=True,usernameFailed=username,passwordFailed=password)


@app.route("/logout", methods=["GET"])
def logout():
    flaskSession.clear()  # Clear the session data
    return redirect(url_for('home'))


#Choose location from a map, or use current location
@app.route("/set-location", methods=["GET"])
def location_menu():
    return render_template("set_location.html")
    

#API call for the next 5 rocket launches
@app.route("/api/next-launch", methods=["GET"])
def next_launch():
    launches, success = get_launches()
    
    return render_template("partials/launch_card.html", launches=launches, success=success)

#API call for 5 recent news articles
@app.route("/api/news", methods=["GET"])
def news():
    news, success = get_news()

    return render_template("partials/news_card.html", news=news, success=success)

#Skyfield API for planetary positions - nice and neat as it has a python library
@app.route("/api/planets", methods=["GET"])
def planets():
    visible_planets = {}

    lat = 51.5074
    lon = -0.1278
    ts = load.timescale()
    time_input = datetime.now().strftime("%H:%M")
    hours, minutes = map(int, time_input.split(":"))
    now = datetime.now(timezone.utc)
    t = ts.utc(now.year, now.month, now.day, hours, minutes, 0)  # Use current year, month, and day
    eph = load('./data/de421.bsp')
    observer = Topos(latitude_degrees=lat, longitude_degrees=lon)

    planet_segments = {
            'Mercury': eph['mercury'],
            'Venus': eph['venus'],
            'Mars': eph['mars'],
            'Jupiter': eph['jupiter barycenter'],
            'Saturn': eph['saturn barycenter'],
            'Uranus': eph['uranus barycenter'],
            'Neptune': eph['neptune barycenter'],
            'Pluto': eph['pluto barycenter']
        }
    
    for name, planet in planet_segments.items():
        astrometric = (eph['earth'] + observer).at(t).observe(planet)
        alt, az, distance = astrometric.apparent().altaz()
        if alt.degrees > 0:
            visible_planets[name] = {
                'altitude': alt.degrees,
                'azimuth': az.degrees,
                'distance': distance.km
            }
    
    return render_template("partials/planets_card.html", planets=visible_planets)



#More information about a specific launch
@app.route("/launch/<launch_id>", methods=["GET"])
def launch_details(launch_id):
    launch, success = get_launch_details(launch_id)

    return render_template("launch_details.html", launch=launch, success=success)

def get_launches(quantity:int=5):
    success = False
    #Prevent too many API calls from being sent using caching
    launches = cache.get("launches")
    if launches == None:
        launches = {}
    if len(launches) < quantity:
        # Fetch from API if not cached
        try:
            launch_response = requests.get(f"https://ll.thespacedevs.com/2.3.0/launches/upcoming/?limit={quantity}")
            if launch_response.ok:
                launches = launch_response.json()["results"]
                launches = {launch['id']: launch for launch in launches}
                cache.set("launches", launches)
                success = True
        except requests.exceptions.SSLError: #Catch errors due to school network not liking me
            success = False
        
    else:
        success = True

    if launches != None:
        launches = [launches[launch_id] for launch_id in launches]
    
    return launches, success

def get_launch_details(launch_id:int):
    success = False
    #Prevent too many API calls from being sent using caching
    launches = cache.get("launches")
    if launches == None:
        launches = {}
    if not launch_id in launches.keys():
        
        # Fetch from API if not cached
        try:
            launch_response = requests.get(f"https://ll.thespacedevs.com/2.3.0/launches/{launch_id}/")
            if launch_response.ok:
                launch = launch_response.json()
                launches[launch['id']] = launch  # Update the cached launches with the new launch details
                cache.set("launches", launches)
                success = True
        except requests.exceptions.SSLError:
            success = False
    else:
        launch = launches[launch_id]
        success = True

    return launch, success

def get_news(quantity:int=5):
    success = False
    #Prevent too many API calls from being sent using caching
    news = cache.get("news")
    if news == None:
        # Fetch from API if not cached
        try:
            news_response = requests.get(f"https://api.spaceflightnewsapi.net/v4/articles/?limit={quantity}")
            if news_response.ok:
                news = news_response.json()["results"]
                news = {article['id']: article for article in news}
                cache.set("news", news)
                success = True
        except requests.exceptions.SSLError:
            success = False
    else:
        success = True
    
    if news != None:
        news = [news[article_id] for article_id in news]
    
    return news, success

# Utility route for password strength
@app.route("/password-strength", methods=["POST"])
def password_strength():
    data = request.json
    password = data.get("password", "")
    score, feedback = scorePassword(password)
    return jsonify({"score": score, "feedback": feedback})

def scorePassword(password):
    passometer = PasswordChecker()
    #Update password checker, then display results
    passometer.update_password(password)

    #Calculates all scores
    passometer.score_length()
    passometer.score_characters()
    passometer.score_rarity()
    #Calculate final score
    passometer.combine_scores(4,3,1)

    passometer.rate_password()

    return passometer.get_score(), passometer.generate_feedback('text')

if __name__ == "__main__":
    app.run(debug=True)