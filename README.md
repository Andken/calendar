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

## Optional systemd auto-start
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

## Notes
- If `OPENWEATHER_API_KEY` is not set, the app will use fallback sample weather data.
- Later, you can add Google Calendar integration and replace the sample event list with real calendar data.
