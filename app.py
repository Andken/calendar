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


AIR_QUALITY_LOCATIONS = [
    {"name": "Tiger Mountain", "lat": 47.4339, "lng": -122.0264},
    {"name": "Cougar Mountain", "lat": 47.5145, "lng": -122.1065},
    {"name": "Downtown Seattle", "lat": 47.6062, "lng": -122.3321},
    {"name": "University of Washington", "lat": 47.6553, "lng": -122.3035},
    {"name": "Ballard", "lat": 47.6686, "lng": -122.3869},
    {"name": "Newcastle", "lat": 47.5437, "lng": -122.1858},
    {"name": "Redmond", "lat": 47.6730, "lng": -122.1215},
    {"name": "Issaquah Highlands", "lat": 47.5375, "lng": -122.0304},
    {"name": "Kirkland", "lat": 47.6769, "lng": -122.2060},
    {"name": "SoDo", "lat": 47.5812, "lng": -122.3301},
    {"name": "Edmonds", "lat": 47.8100, "lng": -122.3770},
    {"name": "Bothell", "lat": 47.7615, "lng": -122.2057},
    {"name": "Woodinville", "lat": 47.7545, "lng": -122.1810},
    {"name": "Maple Valley", "lat": 47.3664, "lng": -122.0448},
    {"name": "Auburn", "lat": 47.3073, "lng": -122.2285},
    {"name": "Snoqualmie", "lat": 47.5337, "lng": -121.8369},
    {"name": "Carnation", "lat": 47.5703, "lng": -121.9149},
    {"name": "Sammamish", "lat": 47.6165, "lng": -122.0353},
]

DEFAULT_AIR_QUALITY_LOCATION = {"lat": 47.6101, "lng": -122.2015}
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "").strip()
PURPLEAIR_API_KEY = os.getenv("PURPLEAIR_API_KEY", "").strip()
AIRNOW_API_KEY = os.getenv("AIRNOW_API_KEY", "").strip()


def aqi_category_and_color(aqi):
    if aqi <= 50:
        return "Good", "#10b981"
    if aqi <= 100:
        return "Moderate", "#f59e0b"
    if aqi <= 150:
        return "Unhealthy for Sensitive Groups", "#f97316"
    if aqi <= 200:
        return "Unhealthy", "#ef4444"
    if aqi <= 300:
        return "Very Unhealthy", "#8b5cf6"
    return "Hazardous", "#a855f7"


def pm25_to_aqi(pm25):
    """Convert PM2.5 (µg/m³) to AQI using EPA breakpoints"""
    if pm25 <= 12:
        return int((pm25 / 12) * 50)
    elif pm25 <= 35.4:
        return int(50 + ((pm25 - 12) / (35.4 - 12)) * 50)
    elif pm25 <= 55.4:
        return int(100 + ((pm25 - 35.4) / (55.4 - 35.4)) * 50)
    elif pm25 <= 150.4:
        return int(150 + ((pm25 - 55.4) / (150.4 - 55.4)) * 50)
    elif pm25 <= 250.4:
        return int(200 + ((pm25 - 150.4) / (250.4 - 150.4)) * 100)
    else:
        return int(300 + ((pm25 - 250.4) / 50) * 50)


def fetch_openaq_aqi(latitude, longitude):
    """Fetch air quality from Open AQ v3 API"""
    if not OPENAQ_API_KEY:
        return None

    try:
        # Step 1: Find locations near the coordinates
        # Open AQ doesn't have a direct geographic query, so we'll search for any locations
        # and get their latest data. For now, get a sample of locations with recent data.
        locations_url = "https://api.openaq.org/v3/locations"
        locations_params = {
            "limit": 100,
            "sort": "-datetimeLast",
        }
        locations_headers = {
            "X-API-Key": OPENAQ_API_KEY,
        }
        
        loc_res = requests.get(locations_url, params=locations_params, headers=locations_headers, timeout=6)
        if loc_res.status_code != 200:
            print(f"Open AQ locations error: {loc_res.status_code}")
            return None
        
        locations_data = loc_res.json()
        locations = locations_data.get("results", [])
        
        if not locations:
            print("Open AQ: No locations found")
            return None
        
        # Step 2: Find the closest location by distance
        min_distance = float('inf')
        closest_location_id = None
        
        for loc in locations:
            if loc.get("datetimeLast"):  # Only consider locations with data
                coords = loc.get("coordinates", {})
                loc_lat = coords.get("latitude")
                loc_lon = coords.get("longitude")
                
                if loc_lat and loc_lon:
                    # Simple distance calculation
                    distance = ((latitude - loc_lat) ** 2 + (longitude - loc_lon) ** 2) ** 0.5
                    if distance < min_distance:
                        min_distance = distance
                        closest_location_id = loc.get("id")
        
        if closest_location_id is None:
            print("Open AQ: No valid location found")
            return None
        
        # Step 3: Get latest measurements for the closest location
        latest_url = f"https://api.openaq.org/v3/locations/{closest_location_id}/latest"
        latest_params = {
            "limit": 100,
        }
        
        lat_res = requests.get(latest_url, params=latest_params, headers=locations_headers, timeout=6)
        if lat_res.status_code != 200:
            print(f"Open AQ latest error: {lat_res.status_code}")
            return None
        
        latest_data = lat_res.json()
        results = latest_data.get("results", [])
        
        # Find PM2.5 measurement
        pm25_value = None
        for result in results:
            # Check if this is a PM2.5 measurement by looking at the sensor
            value = result.get("value")
            if value is not None:
                # Assume first valid numeric value is PM2.5 (or check sensor metadata)
                pm25_value = float(value)
                break
        
        if pm25_value is None:
            print("Open AQ: No PM2.5 value found")
            return None
        
        aqi_val = pm25_to_aqi(pm25_value)
        category, color = aqi_category_and_color(aqi_val)

        return {
            "aqi": aqi_val,
            "category": category,
            "pm2_5": round(pm25_value, 1),
            "color": color,
            "source": "Open AQ",
            "lat": latitude,
            "lng": longitude,
        }
    except Exception as e:
        print(f"Open AQ error: {e}")
        return None


def fetch_purpleair_aqi(latitude, longitude):
    if not PURPLEAIR_API_KEY:
        return None

    url = "https://api.purpleair.com/v1/sensors"
    params = {
        "fields": "pm2.5_60minute",
        "max_age": 3600,
        "lat": latitude,
        "lon": longitude,
        "max_distance": 10000,  # 10km radius
    }
    headers = {
        "X-API-Key": PURPLEAIR_API_KEY,
    }

    try:
        res = requests.get(url, params=params, headers=headers, timeout=6)
        if res.status_code != 200:
            print(f"PurpleAir error: {res.status_code} - {res.text[:200] if res.text else 'No response'}")
            return None
        
        data = res.json()
        sensors = data.get("data", [])
        fields = data.get("fields", [])
        
        if not sensors or len(sensors) == 0:
            return None

        # Find the index of pm2.5_60minute in the fields list
        pm25_index = None
        try:
            pm25_index = fields.index("pm2.5_60minute")
        except ValueError:
            return None

        # Get the first sensor's PM2.5 value
        sensor = sensors[0]
        if not isinstance(sensor, (list, tuple)) or len(sensor) <= pm25_index:
            return None
        
        pm25_value = sensor[pm25_index]
        
        if pm25_value is None or not isinstance(pm25_value, (int, float)):
            return None
        
        pm25_value = float(pm25_value)
        aqi_val = pm25_to_aqi(pm25_value)
        category, color = aqi_category_and_color(aqi_val)

        return {
            "aqi": aqi_val,
            "category": category,
            "pm2_5": round(pm25_value, 1),
            "color": color,
            "source": "PurpleAir",
            "lat": latitude,
            "lng": longitude,
        }
    except requests.exceptions.RequestException as e:
        print(f"PurpleAir request error: {e}")
        return None
    except Exception as e:
        print(f"PurpleAir error: {e}")
        return None


def fetch_airnow_aqi(latitude, longitude):
    if not AIRNOW_API_KEY:
        return None

    url = "https://www.airnowapi.org/aq/observation/latLong/current/"
    params = {
        "format": "application/json",
        "latitude": latitude,
        "longitude": longitude,
        "distance": 25,
        "API_KEY": AIRNOW_API_KEY,
    }

    try:
        res = requests.get(url, params=params, timeout=6)
        res.raise_for_status()
        data = res.json()
        if not isinstance(data, list) or not data:
            return None

        pm25_obs = [obs for obs in data if obs.get("ParameterName") == "PM2.5"]
        obs = pm25_obs[0] if pm25_obs else data[0]
        aqi_val = int(obs.get("AQI", 42))
        category = obs.get("Category", {}).get("Name", "Unknown")
        color = "#10b981"
        if aqi_val <= 50:
            color = "#10b981"
        elif aqi_val <= 100:
            color = "#f59e0b"
        elif aqi_val <= 150:
            color = "#f97316"
        elif aqi_val <= 200:
            color = "#ef4444"
        elif aqi_val <= 300:
            color = "#8b5cf6"
        else:
            color = "#a855f7"

        return {
            "aqi": aqi_val,
            "category": category,
            "pm2_5": None,
            "color": color,
            "source": "AirNow",
            "lat": latitude,
            "lng": longitude,
        }
    except Exception as e:
        print("AirNow fetch error:", e)
        return None


def fetch_open_meteo_aqi(latitude, longitude):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "us_aqi,pm2_5",
        "timezone": "America/Los_Angeles",
    }
    try:
        res = requests.get(url, params=params, timeout=6)
        res.raise_for_status()
        data = res.json()
        curr = data.get("current", {})
        aqi_val = int(curr.get("us_aqi", 42))
        pm25 = round(float(curr.get("pm2_5", 10.0)), 1)
        category, color = aqi_category_and_color(aqi_val)
        return {
            "aqi": aqi_val,
            "category": category,
            "pm2_5": pm25,
            "color": color,
            "source": "Open-Meteo Air Quality",
            "lat": latitude,
            "lng": longitude,
        }
    except Exception as e:
        print("Open-Meteo Air Quality fetch error:", e)

    category, color = aqi_category_and_color(42)
    return {
        "aqi": 42,
        "category": category,
        "pm2_5": 9.5,
        "color": color,
        "source": "Open-Meteo Air Quality",
        "lat": latitude,
        "lng": longitude,
    }


def fetch_air_quality(latitude, longitude):
    # Try Open AQ first (if API key available)
    openaq = fetch_openaq_aqi(latitude, longitude)
    if openaq:
        return openaq
    
    # Fallback to Open-Meteo Air Quality (free, no API key required)
    openmeteo = fetch_open_meteo_aqi(latitude, longitude)
    if openmeteo:
        return openmeteo
    
    # Fallback to PurpleAir (if API key available and account is active)
    purpleair = fetch_purpleair_aqi(latitude, longitude)
    if purpleair:
        return purpleair
    
    # Fallback to AirNow (if API key available)
    airnow = fetch_airnow_aqi(latitude, longitude)
    if airnow:
        return airnow
    
    # Last resort: return default
    category, color = aqi_category_and_color(42)
    return {
        "aqi": 42,
        "category": category,
        "pm2_5": 9.5,
        "color": color,
        "source": "Default",
        "lat": latitude,
        "lng": longitude,
    }



def get_air_quality_locations():
    locations = []
    for location in AIR_QUALITY_LOCATIONS:
        data = fetch_air_quality(location["lat"], location["lng"])
        locations.append({
            "name": location["name"],
            "lat": location["lat"],
            "lng": location["lng"],
            "aqi": data["aqi"],
            "category": data["category"],
            "pm2_5": data["pm2_5"],
            "color": data["color"],
        })
    return locations


def get_air_quality():
    return fetch_air_quality(DEFAULT_AIR_QUALITY_LOCATION["lat"], DEFAULT_AIR_QUALITY_LOCATION["lng"])


@app.route("/")
def index():
    now = datetime.now(SEATTLE_TZ)
    events = get_events()
    return render_template(
        "index.html",
        now=now,
        weather=get_weather(),
        air_quality=get_air_quality(),
        air_quality_locations=get_air_quality_locations(),
        weeks=build_week_grid(events, forecast=get_daily_forecast(days=7)),
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3001"))
    app.run(host="0.0.0.0", port=port, debug=False)
