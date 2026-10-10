"""Environment configuration for AuraX Music."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load local .env for Windows CMD; Render uses dashboard environment variables.
except ImportError:
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_ID = os.getenv("API_ID", "").strip()
API_HASH = os.getenv("API_HASH", "").strip()
SESSION_STRING = os.getenv("SESSION_STRING", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip().lstrip("@")
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot.sqlite3")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()


def validate_config():
    missing = [k for k, v in (("BOT_TOKEN", BOT_TOKEN), ("API_ID", API_ID),
              ("API_HASH", API_HASH), ("SESSION_STRING", SESSION_STRING)) if not v]
    if missing:
        raise RuntimeError("Missing Render environment variables: " + ", ".join(missing))
    try:
        int(API_ID)
    except ValueError as exc:
        raise RuntimeError("API_ID must be a number") from exc
