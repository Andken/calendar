import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from flask import Flask, render_template

# Google Calendar imports (optional)
try:
    from google.oauth2.credentials import Credentials
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GCAL_AVAILABLE = True
except Exception:
    GCAL_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)

DEFAULT_WEATHER = {
    "city": "Austin",
    "temp": "75°F",
    "condition": "Sunny",
    "description": "Clear skies",
    "humidity": 50,
    "wind_kph": 10,
    "high": "78°F",
    "low": "68°F",
    "rain_chance": "10%",
}

SEATTLE_TZ = ZoneInfo("America/Los_Angeles")


def get_default_events():
    today = datetime.now(SEATTLE_TZ).date()
    return [
        {"title": "Morning standup", "time": "09:00-10:00", "location": "Office", "date": (today + timedelta(days=1)).strftime("%Y-%m-%d")},
        {"title": "Lunch with Maya", "time": "12:30-13:30", "location": "Cafeteria", "date": (today + timedelta(days=2)).strftime("%Y-%m-%d")},
        {"title": "Project review", "time": "15:00-16:00", "location": "Conference Room", "date": (today + timedelta(days=4)).strftime("%Y-%m-%d")},
    ]


DEFAULT_EVENTS = get_default_events()


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
        temp_c = data.get("main", {}).get("temp", 0)
        high_c = data.get("main", {}).get("temp_max", temp_c)
        low_c = data.get("main", {}).get("temp_min", temp_c)
        rain_prob = 0
        if data.get("rain"):
            rain_prob = int(data["rain"].get("1h", 0) * 100)
        elif data.get("pop") is not None:
            rain_prob = int(float(data.get("pop", 0)) * 100)
        weather = {
            "city": data.get("name", city),
            "temp": f"{round(temp_c * 9 / 5 + 32)}°F",
            "condition": data.get("weather", [{}])[0].get("main", DEFAULT_WEATHER["condition"]),
            "description": data.get("weather", [{}])[0].get("description", DEFAULT_WEATHER["description"]),
            "humidity": data.get("main", {}).get("humidity", DEFAULT_WEATHER["humidity"]),
            "wind_kph": round(data.get("wind", {}).get("speed", 0) * 3.6),
            "high": f"{round(high_c * 9 / 5 + 32)}°F",
            "low": f"{round(low_c * 9 / 5 + 32)}°F",
            "rain_chance": f"{rain_prob}%",
        }
        return weather
    except requests.RequestException:
        return {**DEFAULT_WEATHER, "city": city}


def get_events():
    # If Google Calendar integration is available and a token exists, fetch events
    if not GCAL_AVAILABLE:
        return get_default_events()

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    now = datetime.now(SEATTLE_TZ).astimezone(timezone.utc)
    time_min = now.isoformat().replace("+00:00", "Z")
    days_ahead = int(os.getenv("GOOGLE_CALENDAR_DAYS_AHEAD", "28").strip() or "28")
    time_max = (now + timedelta(days=days_ahead)).isoformat().replace("+00:00", "Z")
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary").strip() or "primary"

    service = None
    service_account_path = BASE_DIR / "service_account.json"
    token_path = BASE_DIR / "token.json"

    try:
        if service_account_path.exists():
            creds = ServiceAccountCredentials.from_service_account_file(
                str(service_account_path), scopes=SCOPES
            )
            delegated_email = os.getenv("GOOGLE_CALENDAR_DELEGATED_EMAIL", "")
            if delegated_email:
                creds = creds.with_subject(delegated_email)
        elif token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
        else:
            return DEFAULT_EVENTS

        service = build("calendar", "v3", credentials=creds)
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = events_result.get("items", [])
        events = []
        for it in items:
            start = it.get("start", {}).get("dateTime") or it.get("start", {}).get("date")
            end = it.get("end", {}).get("dateTime") or it.get("end", {}).get("date")
            if start and "T" in str(start):
                start_dt = datetime.fromisoformat(str(start).replace("Z", "+00:00")).astimezone(SEATTLE_TZ)
                event_date = start_dt.date().strftime("%Y-%m-%d")
                start_time = start_dt.strftime("%H:%M")
                if end and "T" in str(end):
                    end_dt = datetime.fromisoformat(str(end).replace("Z", "+00:00")).astimezone(SEATTLE_TZ)
                    time_str = f"{start_time}-{end_dt.strftime('%H:%M')}"
                else:
                    time_str = start_time
            else:
                event_date = str(start)
                time_str = str(start)
            events.append(
                {
                    "title": it.get("summary", "(No title)"),
                    "time": time_str,
                    "location": it.get("location", ""),
                    "date": event_date,
                }
            )
        if events:
            return events
    except Exception as e:
        print("Google Calendar fetch error:", e)

    return get_default_events()


def build_week_grid(events):
    today = datetime.now(SEATTLE_TZ).date()
    if today.weekday() == 6:
        start_of_week = today
    else:
        start_of_week = today - timedelta(days=today.weekday() + 1)
    weeks = []

    for week_index in range(4):
        week_start = start_of_week + timedelta(days=week_index * 7)
        days = []
        for offset in range(7):
            day_date = week_start + timedelta(days=offset)
            day_events = [
                event
                for event in events
                if event.get("date") == day_date.strftime("%Y-%m-%d")
            ]
            day_events = sorted(day_events, key=lambda item: item.get("time", ""))
            days.append(
                {
                    "date": day_date,
                    "label": day_date.strftime("%a"),
                    "day": day_date.day,
                    "is_today": day_date == today,
                    "events": day_events,
                }
            )
        weeks.append({"days": days})

    return weeks


@app.route("/")
def index():
    now = datetime.now(SEATTLE_TZ)
    events = get_events()
    return render_template(
        "index.html",
        now=now,
        weather=get_weather(),
        weeks=build_week_grid(events),
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3001"))
    app.run(host="0.0.0.0", port=port, debug=False)
