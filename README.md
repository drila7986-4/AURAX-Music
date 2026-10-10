# AuraX Music Bot — Premium Menu + Music + Games

This project is a Telegram group voice-chat music bot built with Pyrogram, PyTgCalls, yt-dlp and FFmpeg. The source files pass Python syntax compilation, but the bot has **not** been live-tested against your Telegram account, a real group voice chat, or Render. Do not treat static checks as proof of live playback.

## Features present in code

### DM `/start` premium menu
- Premium welcome text and buttons: Add Me to Group, Help/Commands, Ping, Games Zone, Couple Club and Broadcast.
- Add-to-Group URL is filled from the bot's actual Telegram username at startup.
- `/start` records the user as having started the bot in DM. Group commands that require this check will ask the user to start the bot first.

### Music commands
- `/play <song or URL>` and `/vplay <song>`: search YouTube using yt-dlp and resolve a direct audio stream.
- `/pause`, `/resume`, `/skip`, `/stop`, `/end`, `/queue`, `/nowplaying`.
- `/seek <seconds>`, `/seekback <seconds>`, `/volume <0-200>`, `/speed <0.5-2.0>` and `/loop [on|off]` are implemented but need live PyTgCalls/voice-chat testing. FFmpeg flags and API behavior can vary by installed versions.
- `/connect` or `/setgroup` in a group links that group to the command sender for DM music controls.
- `/musicstatus` shows the bot's tracked current track/queue/repeat state. `/vcstatus` reports tracked playback state; it is not a definitive Telegram-side voice-chat diagnostic.
- `/setuser <numeric_user_id>` in a group is owner-only and maps that user's DM music commands to the group.
- Queue and couple membership data use SQLite. The queue is per group.

### Games and Couple Club
- `/wordgame`, `/guess <word>`, `/hint` — hidden word game.
- `/scramble`, `/unscramble <word>` — word scramble.
- `/wordchain` and `/wordchain <word>` — word-chain game.
- `/riddle`, `/answer <word>` — riddle game.
- `/joincouple`, `/leavecouple`, `/couple`, `/love @user1 @user2`.
- Automatic pairing checks opted-in members in registered groups every minute and creates a fresh match when six hours have elapsed since that group's last pairing. `/couple` can trigger a manual pairing. Couple matching is for entertainment only.

### Owner broadcast
- `/broadcast <message>` in DM sends a message to saved user IDs. Set `OWNER_ID` to your numeric Telegram user ID.
- Telegram will reject messages to users who have not started the bot, blocked it, or otherwise cannot be contacted; these are counted as failed sends.

## Provider support and limitations

- **YouTube:** primary source. Searches up to five results and attempts the first playable stream. YouTube changes, geo/age restrictions, unavailable uploads and network restrictions may cause failures.
- **Spotify:** with API credentials, a track URL can resolve to its title/artist, then AuraX searches YouTube. It does not stream Spotify's protected audio.
- **JioSaavn and Gaana:** best-effort public page-title extraction followed by YouTube search. This is **not** direct audio streaming from JioSaavn/Gaana and can fail if their pages change or block requests.
- Auto-next is based on the duration yt-dlp reports. Unknown duration, stalled streams, or mid-track failures can prevent a reliable auto-next. Loop state is in memory and resets after restart.
- Live voice chat is not confirmed until you run the bot with your own credentials and test in a real group. The user session must belong to an account you control and that account must be in the target group with permission to join/speak in the voice chat.

## Windows CMD — run before Render

1. Install **Python 3.11** and enable **Add Python to PATH**.
2. Install **FFmpeg** and ensure `ffmpeg.exe` is on PATH. Verify in CMD with `ffmpeg -version`.
3. Extract this ZIP. Open the `AuraX_Music_Bot` folder.
4. Double-click `setup_windows.bat`, or open CMD in this folder and run:

   ```bat
   setup_windows.bat
   ```

5. Copy `.env.example` to `.env` (the setup script does this if `.env` does not exist) and edit `.env` in Notepad.
6. If you do not already have a Pyrogram user session string, fill `API_ID` and `API_HASH`, then run:

   ```bat
   .venv\Scripts\python.exe generate_session.py
   ```

   Sign in only to your own Telegram account. Copy the printed session string into `.env` as `SESSION_STRING`. Treat it like a password.
7. Run the bot:

   ```bat
   run_bot.bat
   ```

8. In Telegram, DM `/start` to the bot, add it to a group, start a group voice chat, ensure the streaming account is in the group and allowed to speak, then run `/connect` in the group and `/play Arijit Singh Tum Hi Ho`.

## `.env` values

Required:
- `BOT_TOKEN`: bot token from BotFather.
- `API_ID` and `API_HASH`: from https://my.telegram.org.
- `SESSION_STRING`: Pyrogram session string for your own Telegram user account; used to join voice chats.
- `OWNER_ID`: your numeric Telegram user ID; enables owner-only broadcast and `/setuser`.

Recommended/optional:
- `BOT_USERNAME`: bot username without `@`. The bot also fetches its username at startup; this is a fallback for the Add-to-Group button.
- `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`: optional; required only for Spotify track-link metadata lookup.
- `DATABASE_PATH`: local default `bot.sqlite3`. On Render the blueprint sets `/var/data/aurax.sqlite3`; for durable storage, attach a persistent disk mounted at `/var/data` in Render. Without a persistent disk, data may be lost on restart/deploy.
- `LOG_LEVEL`: normally `INFO`.

Never put real tokens/session strings in GitHub, screenshots, or chat messages. `.env` is gitignored; commit `.env.example`, not `.env`.

## Render deployment

1. Push the contents of this project folder to the GitHub repository connected to Render.
2. Create/update a **Background Worker** from the included `render.yaml` or use Docker with the included `Dockerfile`.
3. In Render → Environment, add the same required variables from `.env` (Render does not read your local `.env` file).
4. Deploy, then inspect logs for startup errors.
5. For persistence, add a Render persistent disk mounted at `/var/data` if using `DATABASE_PATH=/var/data/aurax.sqlite3`.
6. Test DM `/start`, Add to Group, `/connect`, `/ping`, `/wordgame`, `/joincouple`, and finally `/play` in a live voice chat.

## Common failures

- `Missing Render environment variables`: fill the required keys in `.env` locally or Render Environment.
- `ffmpeg not found`: install FFmpeg and put its `bin` directory on PATH; Docker image installs FFmpeg automatically.
- `Could not play` / `No playable stream`: update dependencies, inspect yt-dlp output in logs, try another YouTube query, and verify network access.
- Bot responds but no audio: ensure the streaming user session is valid, the account is in the group, a voice chat is active, and it can join/speak. Bot API token alone cannot play Telegram voice chat audio.
- Add-to-Group button missing: verify the bot successfully started and has a public username; then `/start` again.
- Spotify link fails: add valid Spotify client credentials or send the song name and artist instead.
- JioSaavn/Gaana direct playback: not implemented as direct audio sources; current fallback searches YouTube from page metadata.
