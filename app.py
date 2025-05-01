from flask import Flask, render_template
from flask_caching import Cache
from flask import session as flaskSession
import requests
import uuid

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
@app.route("/api/next-launch")
def next_launch():
    launches, success = get_launches()
    
    return render_template("partials/launch_card.html", launches=launches, success=success)

#More information about a specific launch
@app.route("/launch/<launch_id>")
def launch_details(launch_id):
    launch, success = get_launch_details(launch_id)

    return render_template("launch_details.html", launch=launch, success=success)

def get_launches(quantity:int=5):
    success = False
    #Prevent too many API calls from being sent using caching
    launches = cache.get("launches")
    if launches == None:
        # Fetch from API if not cached
        launch_response = requests.get(f"https://ll.thespacedevs.com/2.3.0/launches/upcoming/?limit={quantity}")
        if launch_response.ok:
            launches = launch_response.json()["results"]
            for launch in launches:
                cache.set(f"launch_{launch['id']}", launch)
            success = True
    else:
        success = True
    
    return launches, success

def get_launch_details(launch_id:int):
    success = False
    #Prevent too many API calls from being sent using caching
    launch = cache.get(f"launch_{launch_id}")
    if not launch:
        # Fetch from API if not cached
        launch_response = requests.get(f"https://ll.thespacedevs.com/2.3.0/launches/{launch_id}/")
        if launch_response.ok:
            launch = launch_response.json()
            cache.set(f"launch_{launch_id}", launch)  # Cache the launch details
            success = True
    else:
        success = True

    return launch, success

if __name__ == "__main__":
    app.run(debug=True)