"""One-time helper to obtain `token.json` for Google Calendar API.

Usage:
  1. Create OAuth credentials (Desktop) in Google Cloud Console and download
     the JSON as `client_secrets.json` into this project folder.
  2. Run this on a machine with a browser:
     python3 get_token.py
  3. Copy the created `token.json` to the Pi project directory.
"""
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

BASE_DIR = Path(__file__).resolve().parent
CLIENT_SECRETS = BASE_DIR / "client_secrets.json"
TOKEN_FILE = BASE_DIR / "token.json"

if not CLIENT_SECRETS.exists():
    print("client_secrets.json not found in project folder. Create OAuth credentials and save as client_secrets.json")
    raise SystemExit(1)

flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
creds = flow.run_local_server(port=0)
with open(TOKEN_FILE, "w") as f:
    f.write(creds.to_json())
print("Saved token.json")
