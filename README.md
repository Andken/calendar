# Raspberry Pi Calendar Dashboard

A lightweight Flask dashboard that shows the current time, local weather, and upcoming events. This project is designed to run on a Raspberry Pi in full-screen kiosk mode.

## What is included
- `app.py` — Flask web server
- `templates/index.html` — dashboard UI template
- `static/style.css` — dashboard styles
- `requirements.txt` — Python dependencies
- `.env.example` — environment configuration example
- `calendar-dashboard.service` — optional systemd service template for Raspberry Pi

## Raspberry Pi setup
1. Copy the project to your Raspberry Pi, for example:
   ```bash
   scp -r /Users/bendev/projects/calendar pi@<raspberry-pi-ip>:/home/pi/calendar
   ```

2. SSH into the Pi:
   ```bash
   ssh pi@<raspberry-pi-ip>
   ```

3. Install Python tools:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip
   ```

4. Create and activate a virtual environment:
   ```bash
   cd /home/pi/calendar
   python3 -m venv .venv
   source .venv/bin/activate
   ```

5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

6. Copy the example env file and update the settings:
   ```bash
   cp .env.example .env
   ```

## Run locally on the Pi
```bash
source .venv/bin/activate
python3 app.py
```
Then open `http://<raspberry-pi-ip>:3001` from another computer.

## Kiosk mode
On a Raspberry Pi with desktop installed, you can run Chromium in kiosk mode:
```bash
chromium-browser --kiosk http://localhost:3001
```

## Optional systemd auto-start for the Flask app
Copy `calendar-dashboard.service` to `/etc/systemd/system/` and enable it:
```bash
sudo cp calendar-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now calendar-dashboard.service
```

Check status:
```bash
sudo systemctl status calendar-dashboard.service
```

## Start Chromium on desktop login (recommended)
Instead of using systemd for Chromium, it is more reliable to launch the browser from the Pi desktop session.

Copy the desktop autostart file:
```bash
mkdir -p /home/pi/.config/autostart
cp /home/pi/calendar/autostart.desktop /home/pi/.config/autostart/
chmod +x /home/pi/calendar/start-kiosk.sh
```

Then reboot the Pi and Chromium should open once the desktop session starts.


## Google Calendar integration
The app supports two Google Calendar auth modes:

### 1) OAuth client flow
1. Create OAuth credentials (Desktop app) in Google Cloud Console.
2. Download `client_secrets.json` into your project folder.
3. Run:
   ```bash
   python3 get_token.py
   ```
4. Copy `token.json` to the Pi project folder.

### 2) Service account flow
1. Create a service account in Google Cloud Console.
2. Download the JSON key and save it as `service_account.json` in the project folder, or copy `service_account.example.json` and update the placeholder values.
3. Share the target calendar with the service account email, or set a delegated user.
4. Add this to `.env`:
   ```bash
   GOOGLE_CALENDAR_DELEGATED_EMAIL=user@example.com
   ```
5. Restart the Flask app.

The service account path is `service_account.json`, and `GOOGLE_CALENDAR_DELEGATED_EMAIL` is optional but required for delegated access.

## Notes
- `service_account.json`, `client_secrets.json`, and `token.json` are ignored by `.gitignore`.
- If `OPENWEATHER_API_KEY` is not set, the app will use fallback sample weather data.
- Later, you can add additional calendar sources or make event styling more prominent.
