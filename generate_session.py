"""One-time helper to generate a Pyrogram user session string for an account you own."""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from pyrogram import Client

load_dotenv(Path(__file__).with_name('.env'))
api_id = os.getenv('API_ID', '').strip()
api_hash = os.getenv('API_HASH', '').strip()
if not api_id or not api_hash:
    raise SystemExit('Fill API_ID and API_HASH in .env first.')

async def main():
    app = Client('aurax_session_generator', api_id=int(api_id), api_hash=api_hash, in_memory=True)
    await app.start()
    try:
        print('\nSESSION_STRING (keep private; paste it into .env as SESSION_STRING):\n')
        print(await app.export_session_string())
    finally:
        await app.stop()

if __name__ == '__main__':
    asyncio.run(main())
