import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, render_template

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)

DEFAULT_WEATHER = {
    "city": "Austin",
    "temp": "24°C",
    "condition": "Sunny",
    "description": "Clear skies",
    "humidity": 50,
    "wind_kph": 10,
}

DEFAULT_EVENTS = [
    {"title": "Morning standup", "time": "09:00", "location": "Office"},
    {"title": "Lunch with Maya", "time": "12:30", "location": "Cafeteria"},
    {"title": "Project review", "time": "15:00", "location": "Conference Room"},
]


def get_weather():
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    city = os.getenv("OPENWEATHER_CITY", "Austin").strip()

    if not api_key:
        return {**DEFAULT_WEATHER, "city": city}

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
    }

    try:
        response = requests.get(url, params=params, timeout=6)
        response.raise_for_status()
        data = response.json()
        weather = {
            "city": data.get("name", city),
            "temp": f"{round(data.get('main', {}).get('temp', 0))}°C",
            "condition": data.get("weather", [{}])[0].get("main", DEFAULT_WEATHER["condition"]),
            "description": data.get("weather", [{}])[0].get("description", DEFAULT_WEATHER["description"]),
            "humidity": data.get("main", {}).get("humidity", DEFAULT_WEATHER["humidity"]),
            "wind_kph": round(data.get("wind", {}).get("speed", 0) * 3.6),
        }
        return weather
    except requests.RequestException:
        return {**DEFAULT_WEATHER, "city": city}


def get_events():
    return DEFAULT_EVENTS


@app.route("/")
def index():
    now = datetime.now()
    return render_template(
        "index.html",
        now=now,
        weather=get_weather(),
        events=get_events(),
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3001"))
    app.run(host="0.0.0.0", port=port, debug=False)
