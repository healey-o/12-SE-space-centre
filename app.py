from flask import Flask, render_template
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/next-launch")
def next_launch():
    launches = []
    try:
        launch_response = requests.get("https://ll.thespacedevs.com/2.3.0/launches/upcoming/?limit=5")
        if launch_response.ok:
            launches = launch_response.json()["results"]
    except:
        pass

    return render_template("partials/launch_card.html", launches=launches)

if __name__ == "__main__":
    app.run(debug=True)