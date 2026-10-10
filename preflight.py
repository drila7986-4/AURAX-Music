"""Local configuration check that does not print secret values."""
import os
import shutil
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name('.env'))
except ImportError:
    pass

required = ['BOT_TOKEN', 'API_ID', 'API_HASH', 'SESSION_STRING', 'OWNER_ID']
missing = [key for key in required if not os.getenv(key, '').strip() or os.getenv(key, '').startswith('PASTE_')]
if missing:
    print('ERROR: Fill these values in .env: ' + ', '.join(missing))
    sys.exit(1)
try:
    int(os.getenv('API_ID', ''))
    int(os.getenv('OWNER_ID', ''))
except ValueError:
    print('ERROR: API_ID and OWNER_ID must be numeric integers.')
    sys.exit(1)
if not os.getenv('BOT_USERNAME', '').strip() or os.getenv('BOT_USERNAME', '').startswith('YOUR_'):
    print('WARNING: BOT_USERNAME is blank/placeholder. The bot normally fetches it from Telegram at startup; set it to the bot username without @ if Add-to-Group is missing.')
if not shutil.which('ffmpeg'):
    print('WARNING: FFmpeg was not found on PATH. Telegram music playback will likely fail until FFmpeg is installed.')
print('Configuration variables look filled. Secrets were not displayed.')
print('Note: this check cannot verify that tokens/session are valid or that Telegram Voice Chat will work.')
