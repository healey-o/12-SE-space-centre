from flask import Flask, render_template
from flask_caching import Cache
from flask import session as flaskSession
import requests
import uuid
from skyfield.api import load, Topos, load_constellation_map, Star, load_constellation_names
from datetime import datetime, timezone


app = Flask(__name__)

# Configure Flask Caching
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
cache = Cache(app)

#Secret key for session management
app.secret_key = str(uuid.uuid4())

#Dashboard
@app.route("/")
def home():
    return render_template("index.html")

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

if __name__ == "__main__":
    app.run(debug=True)