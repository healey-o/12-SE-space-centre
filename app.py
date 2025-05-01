from flask import Flask, render_template
from flask import session as flaskSession
import requests
import uuid

app = Flask(__name__)

#Secret key and Flask session
app.secret_key = str(uuid.uuid4())

#Dashboard
@app.route("/")
def home():
    return render_template("index.html")

#API call for the next 5 rocket launches
@app.route("/api/next-launch")
def next_launch():
    #Prevent too many API calls from being sent
    success = False
    if 'launches' not in flaskSession:
        launches = []
        launch_response = requests.get("https://ll.thespacedevs.com/2.3.0/launches/upcoming/?limit=5")
        if launch_response.ok:
            launches = launch_response.json()["results"]
            flaskSession['launches'] = launches
            success = True
    else:
        launches = flaskSession['launches']
        success = True
    
    return render_template("partials/launch_card.html", launches=launches, success=success)

#More information about a specific launch
@app.route("/launch/<launch_id>")
def launch_details(launch_id):
    success = False
    #Only get the launch details if it has not already been fetched
    if 'launches' not in flaskSession:
        launch = {}
        launch_response = requests.get(f"https://ll.thespacedevs.com/2.3.0/launches/{launch_id}/")
        if launch_response.ok:
            launch = launch_response.json()
            success = True
    else:
        # Get the launch details from the session if it has already been fetched
        launches = flaskSession['launches']
        launch = next((launch for launch in launches if launch['id'] == int(launch_id)), {})
        if launch == {}:
            # If the launch is not in the session, fetch it from the API
            launch_response = requests.get(f"https://ll.thespacedevs.com/2.3.0/launches/{launch_id}/")
            if launch_response.ok:
                launch = launch_response.json()
                success = True
        else:
            success = True

    return render_template("launch_details.html", launch=launch, success=success)

if __name__ == "__main__":
    app.run(debug=True)