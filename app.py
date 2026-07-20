from datetime import datetime
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    now = datetime.now()
    weather = {
        "city": "Austin",
        "temp": "24°C",
        "condition": "Sunny"
    }
    events = [
        {"title": "Morning standup", "time": "09:00"},
        {"title": "Lunch with Maya", "time": "12:30"},
        {"title": "Project review", "time": "15:00"},
    ]
    return render_template(
        "index.html",
        now=now,
        weather=weather,
        events=events
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3001, debug=False)
