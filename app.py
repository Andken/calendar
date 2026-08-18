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
    "city": "Bellevue, WA 98005",
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
        {"title": "Morning Coffee", "time": "08:30-09:00", "location": "Kitchen", "date": today.strftime("%Y-%m-%d")},
        {"title": "Team Sync", "time": "11:00-11:30", "location": "Zoom", "date": today.strftime("%Y-%m-%d")},
        {"title": "Morning standup", "time": "09:00-10:00", "location": "Office", "date": (today + timedelta(days=1)).strftime("%Y-%m-%d")},
        {"title": "Lunch with Maya", "time": "12:30-13:30", "location": "Cafeteria", "date": (today + timedelta(days=2)).strftime("%Y-%m-%d")},
        {"title": "Project review", "time": "15:00-16:00", "location": "Conference Room", "date": (today + timedelta(days=4)).strftime("%Y-%m-%d")},
    ]


DEFAULT_EVENTS = get_default_events()


def get_weather():
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    city = os.getenv("OPENWEATHER_CITY", "98005,US").strip()
    display_city = DEFAULT_WEATHER["city"]

    if "98005" in city.upper() or "BELLEVUE" in city.upper():
        latitude, longitude = 47.6101, -122.2015
        display_city = "Bellevue, WA 98005"
    else:
        latitude, longitude = None, None

    if api_key and latitude is None and longitude is None:
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
            return {**DEFAULT_WEATHER, "city": display_city}

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code,windspeed_10m,precipitation_probability",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_mean",
        "timezone": "America/Los_Angeles",
        "temperature_unit": "fahrenheit",
        "windspeed_unit": "mph",
        "precipitation_unit": "inch",
    }

    try:
        response = requests.get(url, params=params, timeout=6)
        response.raise_for_status()
        data = response.json()
        current = data.get("current", {})
        daily = data.get("daily", {})
        daily_max = daily.get("temperature_2m_max", [current.get("temperature_2m", 0)])
        daily_min = daily.get("temperature_2m_min", [current.get("temperature_2m", 0)])
        daily_rain = daily.get("precipitation_probability_mean", [current.get("precipitation_probability", 0)])
        weather_code = current.get("weather_code", 0)
        condition_map = {
            0: ("Clear", "Clear sky"),
            1: ("Mainly Clear", "Mainly clear"),
            2: ("Partly Cloudy", "Partly cloudy"),
            3: ("Cloudy", "Cloudy"),
            45: ("Fog", "Fog"),
            48: ("Rime Fog", "Rime fog"),
            51: ("Light Drizzle", "Light drizzle"),
            53: ("Drizzle", "Drizzle"),
            55: ("Heavy Drizzle", "Heavy drizzle"),
            61: ("Light Rain", "Light rain"),
            63: ("Rain", "Rain"),
            65: ("Heavy Rain", "Heavy rain"),
            71: ("Light Snow", "Light snow"),
            73: ("Snow", "Snow"),
            75: ("Heavy Snow", "Heavy snow"),
            95: ("Thunderstorm", "Thunderstorm"),
        }
        condition, description = condition_map.get(weather_code, (DEFAULT_WEATHER["condition"], DEFAULT_WEATHER["description"]))
        weather = {
            "city": display_city,
            "temp": f"{round(float(current.get('temperature_2m', 0)))}°F",
            "condition": condition,
            "description": description,
            "humidity": current.get("relative_humidity_2m", DEFAULT_WEATHER["humidity"]),
            "wind_kph": round(float(current.get("windspeed_10m", 0)) * 1.60934),
            "high": f"{round(float(daily_max[0] if daily_max else current.get('temperature_2m', 0)))}°F",
            "low": f"{round(float(daily_min[0] if daily_min else current.get('temperature_2m', 0)))}°F",
            "rain_chance": f"{int(float(daily_rain[0] if daily_rain else current.get('precipitation_probability', 0)))}%",
        }
        return weather
    except requests.RequestException:
        return {**DEFAULT_WEATHER, "city": display_city}


def get_daily_forecast(days=5):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 47.6101,
        "longitude": -122.2015,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_mean",
        "timezone": "America/Los_Angeles",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
    }

    try:
        response = requests.get(url, params=params, timeout=6)
        response.raise_for_status()
        data = response.json()
        daily = data.get("daily", {})
        times = daily.get("time", [])
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])
        rains = daily.get("precipitation_probability_mean", [])

        forecast = []
        for index in range(min(days, len(times))):
            forecast.append(
                {
                    "date": times[index],
                    "high": f"{round(float(highs[index]))}°F",
                    "low": f"{round(float(lows[index]))}°F",
                    "rain": f"{int(float(rains[index]))}%",
                }
            )
        if forecast:
            return forecast
    except requests.RequestException:
        pass

    today = datetime.now(SEATTLE_TZ).date()
    return [
        {
            "date": (today + timedelta(days=offset)).strftime("%Y-%m-%d"),
            "high": DEFAULT_WEATHER["high"],
            "low": DEFAULT_WEATHER["low"],
            "rain": DEFAULT_WEATHER["rain_chance"],
        }
        for offset in range(days)
    ]


def get_events():
    # If Google Calendar integration is available and a token exists, fetch events
    if not GCAL_AVAILABLE:
        return get_default_events()

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    now = datetime.now(SEATTLE_TZ)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    time_min = start_of_today.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    days_ahead = int(os.getenv("GOOGLE_CALENDAR_DAYS_AHEAD", "28").strip() or "28")
    time_max = (now + timedelta(days=days_ahead)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
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


def build_week_grid(events, forecast=None):
    today = datetime.now(SEATTLE_TZ).date()
    if today.weekday() == 6:
        start_of_week = today
    else:
        start_of_week = today - timedelta(days=today.weekday() + 1)
    weeks = []

    forecast_by_date = {}
    if forecast:
        for item in forecast:
            forecast_by_date[item.get("date")] = item

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
            day_key = day_date.strftime("%Y-%m-%d")
            days.append(
                {
                    "date": day_date,
                    "label": day_date.strftime("%a"),
                    "month": day_date.strftime("%b"),
                    "day": day_date.day,
                    "is_today": day_date == today,
                    "events": day_events,
                    "forecast": forecast_by_date.get(day_key),
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
        weeks=build_week_grid(events, forecast=get_daily_forecast(days=7)),
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3001"))
    app.run(host="0.0.0.0", port=port, debug=False)
