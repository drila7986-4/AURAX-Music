"""AuraX Music: Telegram VC music bot (Pyrogram + PyTgCalls)."""
import asyncio, logging, time, random, hashlib
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, API_ID, API_HASH, SESSION_STRING, OWNER_ID, BOT_USERNAME, LOG_LEVEL, validate_config
from database import init_db, save_user, mark_started_dm, link_group, get_linked_group, all_user_ids, has_started_dm, register_game_group, join_game, leave_game, game_members, game_group_ids, get_last_pairing, set_last_pairing
from music import MusicManager

logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO), format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
log = logging.getLogger('aurax-music')
validate_config()
bot = Client('aurax_bot', api_id=int(API_ID), api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client('aurax_streamer', api_id=int(API_ID), api_hash=API_HASH, session_string=SESSION_STRING)
from pytgcalls import PyTgCalls
calls = PyTgCalls(user)
music = MusicManager(calls)

START = ('╭━━━『 💎 **AURAX PREMIUM** 』━━━╮\n'
         '🎧 Music • 🎮 Games • 💞 Couple Club\n'
         '╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
         '✨ Welcome! Main AuraX hoon — aapka premium-style music & fun bot.\n\n'
         '🎵 **Music:** YouTube search, play, queue & controls\n'
         '🎮 **Games:** Hidden Word, Scramble, Word Chain & Riddles\n'
         '💞 **Couple Club:** Love percentage aur opt-in matching\n'
         '⏰ Couple matching: opted-in members ke liye har 6 ghante\n\n'
         '🚀 **Shuru kaise karein:** Add Me to Group dabayein, bot ko group mein add karein, phir group mein /connect use karein. Music ke liye voice chat aur streaming account zaroori hai.\n\n'
         '👇 Neeche buttons se Help, Ping, Couple Club aur Owner Broadcast details dekhein.')
HELP = ('**🎵 AuraX Music commands**\n'
        '`/play <song or URL>` — play or queue (YouTube search / Spotify track link)\n'
        '`/vplay <song>` — alias for play\n`/pause` · `/resume` · `/skip`\n'
        '`/stop` · `/end` · `/queue` · `/nowplaying` · `/loop [on|off]`\n`/connect` · `/setgroup` · `/setuser` · `/ping` · `/id`\n`/musicstatus` · `/vcstatus`\n'
        '`/seek <seconds>` · `/seekback <seconds>` · `/volume <0-200>` · `/speed <0.5-2.0>`\n'
        '`/broadcast <message>` — owner only\n\n**🎮 Games**\n`/wordgame` — hidden word game\n`/guess <word>` — guess the hidden word\n`/hint` — hint for current word\n`/scramble` — unscramble a word\n`/joincouple` / `/leavecouple` — opt in/out\n`/couple` — generate a couple now\n`/love @user1 @user2` — compatibility percentage\n\nCouples rotate every 6 hours among opted-in players.')


def home_keyboard():
    rows = []
    if BOT_USERNAME:
        rows.append([InlineKeyboardButton('➕ ADD ME TO GROUP', url=f'https://t.me/{BOT_USERNAME}?startgroup=true')])
    rows.append([
        InlineKeyboardButton('📚 HELP / COMMANDS', callback_data='aurax_help'),
        InlineKeyboardButton('🏓 PING', callback_data='aurax_ping'),
    ])
    rows.append([
        InlineKeyboardButton('🎮 GAMES ZONE', callback_data='aurax_games'),
        InlineKeyboardButton('💞 COUPLE CLUB', callback_data='aurax_couple'),
    ])
    rows.append([InlineKeyboardButton('📢 BROADCAST', callback_data='aurax_broadcast')])
    return InlineKeyboardMarkup(rows)


def is_group(message):
    return message.chat.type in ('group', 'supergroup')

async def target_chat(message):
    if is_group(message): return message.chat.id
    return get_linked_group(message.from_user.id) if message.from_user else None

@bot.on_message(filters.private & filters.command('start'))
async def start_cmd(_, message):
    save_user(message.from_user)
    if message.from_user:
        mark_started_dm(message.from_user.id)
    await message.reply_text(START, reply_markup=home_keyboard())

@bot.on_callback_query(filters.regex('^aurax_help$'))
async def help_cb(_, query):
    await query.answer(); await query.message.reply_text(HELP, reply_markup=home_keyboard())

@bot.on_callback_query(filters.regex('^aurax_ping$'))
async def ping_cb(_, query):
    await query.answer('🏓 AuraX is online!', show_alert=True)

@bot.on_callback_query(filters.regex('^aurax_games$'))
async def games_cb(_, query):
    await query.answer()
    games_text = (
        '╭━━━『 🎮 **AURAX GAMES ZONE** 』━━━╮\n'
        '🕵️ `/wordgame` — hidden word guess\n'
        '💡 `/hint` — hint for the active word\n'
        '🔤 `/scramble` — unscramble letters\n'
        '✍️ `/unscramble <word>` — submit your answer\n'
        '🔗 `/wordchain` — start word chain\n'
        '🧠 `/riddle` — get a riddle\n'
        '🏆 `/answer <word>` — answer the riddle\n'
        '💞 `/joincouple` — join opt-in couple club\n'
        '💔 `/leavecouple` — leave couple club\n'
        '💘 `/love @user1 @user2` — fun love percentage\n'
        '✨ `/couple` — create a manual pairing\n'
        '╰━━━━━━━━━━━━━━━━━━━━╯\n\n'
        'Games are played in groups. Pehle DM mein `/start` karein, phir bot ko group mein add karein.\n'
        'Couple matching sirf opt-in members ke liye hai; users can leave anytime.'
    )
    await query.message.reply_text(games_text, reply_markup=home_keyboard())


@bot.on_callback_query(filters.regex('^aurax_couple$'))
async def couple_cb(_, query):
    await query.answer()
    await query.message.reply_text(
        '💞 **AURAX COUPLE CLUB** 💞\n\n'
        '1. Bot ko group mein add karein.\n'
        '2. Group mein `/joincouple` bhejein.\n'
        '3. `/love @user1 @user2` se fun compatibility dekhein.\n'
        '4. Opted-in members ke liye automatic pairing har 6 ghante check hoti hai.\n\n'
        '✨ Ye feature sirf fun ke liye hai. `/leavecouple` se kabhi bhi opt out kar sakte hain.',
        reply_markup=home_keyboard())

@bot.on_callback_query(filters.regex('^aurax_broadcast$'))
async def broadcast_cb(_, query):
    await query.answer()
    if not OWNER_ID or not query.from_user or query.from_user.id != OWNER_ID:
        return await query.message.reply_text('🔒 **Owner-only feature**\nBroadcast use karne ke liye bot owner ko DM mein `/broadcast your message` bhejna hoga.')
    await query.message.reply_text('📢 **OWNER BROADCAST**\n\nDM mein `/broadcast your message` bhejein. Ye message un users ko jayega jinhone bot ko pehle `/start` kiya hai.', reply_markup=home_keyboard())

@bot.on_message(filters.command('help'))
async def help_cmd(_, message):
    if message.chat.type == 'private': save_user(message.from_user)
    await message.reply_text(HELP)

@bot.on_message(filters.command('connect') & filters.group)
async def connect_cmd(_, message):
    if not message.from_user: return
    if not has_started_dm(message.from_user.id):
        return await message.reply_text('🔐 Pehle mujhe DM mein /start bhejiye, phir group mein /connect use karein.')
    register_game_group(message.chat.id, message.chat.title or '')
    link_group(message.from_user.id, message.chat.id)
    await message.reply_text('✅ Group linked to your account. You can now DM me `/play song name`.')

@bot.on_message(filters.command(['play', 'vplay']))
async def play_cmd(_, message):
    if is_group(message) and message.from_user and not has_started_dm(message.from_user.id):
        return await message.reply_text('🔐 Pehle mujhe DM mein /start bhejiye, phir group mein gaana play karein.')
    save_user(message.from_user)
    if is_group(message): register_game_group(message.chat.id, message.chat.title or '')
    query = ' '.join(message.command[1:]).strip()
    if not query: return await message.reply_text('Usage: `/play song name` or `/vplay song name`')
    chat_id = await target_chat(message)
    if not chat_id: return await message.reply_text('First run `/connect` in the target group, then DM `/play song name`.')
    try:
        status = await music.play(chat_id, query, message.from_user.id if message.from_user else 0)
        await message.reply_text(status)
    except Exception as exc:
        log.exception('play failed'); await message.reply_text(f'❌ Could not play: {type(exc).__name__}: {exc}\nCheck active VC, streaming account permissions, and Render logs.')

async def control_chat(message):
    chat_id = await target_chat(message)
    if not chat_id: await message.reply_text('Use `/connect` in the target group first.'); return None
    return chat_id

@bot.on_message(filters.command('pause'))
async def pause_cmd(_, message):
    chat_id = await control_chat(message)
    if chat_id:
        try: await music.pause(chat_id); await message.reply_text('⏸️ Paused.')
        except Exception as exc: await message.reply_text(f'Pause failed: {exc}')

@bot.on_message(filters.command('resume'))
async def resume_cmd(_, message):
    chat_id = await control_chat(message)
    if chat_id:
        try: await music.resume(chat_id); await message.reply_text('▶️ Resumed.')
        except Exception as exc: await message.reply_text(f'Resume failed: {exc}')

@bot.on_message(filters.command('skip'))
async def skip_cmd(_, message):
    chat_id = await control_chat(message)
    if not chat_id: return
    try:
        await calls.leave_call(chat_id); music.current.pop(chat_id, None)
        if await music.next_track(chat_id): await message.reply_text('⏭️ Skipped to next track.')
        else: await message.reply_text('Queue ended; nothing else to play.')
    except Exception as exc: await message.reply_text(f'Skip failed: {exc}')

@bot.on_message(filters.command(['stop', 'end']))
async def stop_cmd(_, message):
    chat_id = await control_chat(message)
    if chat_id:
        try: await music.stop(chat_id); await message.reply_text('⏹️ Stopped and cleared queue.')
        except Exception as exc: await message.reply_text(f'Stop failed: {exc}')

@bot.on_message(filters.command('queue'))
async def queue_cmd(_, message):
    chat_id = await control_chat(message)
    if chat_id: await message.reply_text(music.queue_text(chat_id))

@bot.on_message(filters.command('nowplaying'))
async def nowplaying_cmd(_, message):
    chat_id = await target_chat(message); current = music.current.get(chat_id) if chat_id else None
    await message.reply_text(f"🎶 Now playing: {current['title']}" if current else 'Nothing is currently playing.')

@bot.on_message(filters.command('ping'))
async def ping_cmd(_, message): await message.reply_text('🏓 AuraX Music is online.')

@bot.on_message(filters.command('setgroup') & filters.group)
async def setgroup_cmd(_, message):
    if not message.from_user:
        return
    if not has_started_dm(message.from_user.id):
        return await message.reply_text('🔐 Pehle DM mein /start karein, phir /setgroup use karein.')
    register_game_group(message.chat.id, message.chat.title or '')
    link_group(message.from_user.id, message.chat.id)
    await message.reply_text('✅ Aapka DM music-control group set ho gaya. Ab DM mein /play song name bhej sakte hain.')

@bot.on_message(filters.command('setuser') & filters.group)
async def setuser_cmd(_, message):
    if not message.from_user or message.from_user.id != OWNER_ID:
        return await message.reply_text('🔒 /setuser sirf bot owner use kar sakta hai.')
    if len(message.command) < 2 or not message.command[1].lstrip('-').isdigit():
        return await message.reply_text('Usage (owner only, group mein): `/setuser <numeric_user_id>`\nUs user ke DM music controls ko is group se link karega.')
    target_id = int(message.command[1])
    link_group(target_id, message.chat.id)
    register_game_group(message.chat.id, message.chat.title or '')
    await message.reply_text(f'✅ User `{target_id}` ka DM music-control group set ho gaya.')

@bot.on_message(filters.command('musicstatus'))
async def musicstatus_cmd(_, message):
    chat_id = await target_chat(message)
    if not chat_id:
        return await message.reply_text('No group linked. Group mein /connect ya /setgroup use karein.')
    current = music.current.get(chat_id)
    queue_count = len(music.queue_text(chat_id).splitlines()) if music.queue_text(chat_id) != 'Queue is empty.' else 0
    title = current.get('title', 'Nothing playing') if current else 'Nothing playing'
    loop = 'ON' if music.loop_modes.get(chat_id, False) else 'OFF'
    await message.reply_text(f'🎵 **MUSIC STATUS**\nNow playing: {title}\nQueue items: {queue_count}\nRepeat current: {loop}')

@bot.on_message(filters.command('vcstatus'))
async def vcstatus_cmd(_, message):
    chat_id = await target_chat(message)
    if not chat_id:
        return await message.reply_text('No group linked. Group mein /connect use karein.')
    current = music.current.get(chat_id)
    if current:
        await message.reply_text(f'🎙️ Voice playback state: active\nTrack: {current.get("title", "Unknown")}\nNote: actual Telegram voice-chat membership still depends on the streaming account and PyTgCalls.')
    else:
        await message.reply_text('🎙️ Bot ke paas is group ke liye active track nahi hai. Voice Chat status ko Telegram par manually verify karein.')

@bot.on_message(filters.command('loop'))
async def loop_cmd(_, message):
    chat_id = await control_chat(message)
    if not chat_id:
        return
    arg = message.command[1].lower() if len(message.command) > 1 else ''
    if arg in ('on', '1', 'true'):
        enabled = True
    elif arg in ('off', '0', 'false'):
        enabled = False
    elif not arg:
        enabled = not music.loop_modes.get(chat_id, False)
    else:
        return await message.reply_text('Usage: `/loop`, `/loop on`, or `/loop off`.')
    music.loop_modes[chat_id] = enabled
    await message.reply_text('🔁 Repeat current track: **ON**' if enabled else '➡️ Repeat current track: **OFF**')

@bot.on_message(filters.command('id'))
async def id_cmd(_, message):
    await message.reply_text(f'Chat ID: `{message.chat.id}`\nUser ID: `{message.from_user.id if message.from_user else "unknown"}`')

@bot.on_message(filters.command(['seek', 'seekback']))
async def seek_cmd(_, message):
    chat_id = await control_chat(message)
    if not chat_id: return
    if len(message.command) < 2 or not message.command[1].lstrip('-').isdigit():
        return await message.reply_text('Usage: `/seek 90` or `/seekback 15` (seconds).')
    amount = int(message.command[1])
    target = amount if message.command[0].lower() == 'seek' else max(0, music.elapsed(chat_id) - amount)
    try:
        await music.seek(chat_id, target)
        await message.reply_text(f'⏩ Jumped to {target} seconds.')
    except Exception as exc:
        await message.reply_text(f'Seek failed: {exc}')

@bot.on_message(filters.command('volume'))
async def volume_cmd(_, message):
    chat_id = await control_chat(message)
    if not chat_id: return
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text('Usage: `/volume 100` (0–200).')
    volume = int(message.command[1])
    if not 0 <= volume <= 200:
        return await message.reply_text('Volume must be between 0 and 200.')
    try:
        await calls.change_volume_call(chat_id, volume)
        music.volumes[chat_id] = volume
        await message.reply_text(f'🔊 Volume set to {volume}%.')
    except Exception as exc:
        await message.reply_text(f'Volume change failed: {exc}. Make sure the streaming account is connected to the voice chat.')

@bot.on_message(filters.command('speed'))
async def speed_cmd(_, message):
    chat_id = await control_chat(message)
    if not chat_id: return
    try:
        speed = float(message.command[1]) if len(message.command) > 1 else 0
        await music.set_speed(chat_id, speed)
        await message.reply_text(f'⏩ Playback speed set to {speed:g}x.')
    except Exception as exc:
        await message.reply_text(f'Usage: `/speed 1.25` (0.5–2.0). Error: {exc}')


# ---------------- Premium-style word and couple games ----------------
WORDS = [
    ('RAINBOW', '🌈 Aasman mein baarish ke baad dikhne wali rang-birangi cheez.'),
    ('PYTHON', '🐍 Ek programming language bhi aur ek saanp bhi.'),
    ('FRIEND', '🤝 Jo mushkil waqt mein saath de.'),
    ('MUSIC', '🎵 Jise sun kar mood fresh hota hai.'),
    ('PLANET', '🪐 Earth bhi isi category mein aati hai.'),
    ('PUZZLE', '🧩 Dimaag lagakar solve karte hain.'),
    ('DIAMOND', '💎 Bahut keemti ratna.'),
    ('GARDEN', '🌻 Jahan phool aur paudhe ugte hain.'),
    ('CHOCOLATE', '🍫 Meethi treat jo cocoa se banti hai.'),
    ('SUNSHINE', '☀️ Dhoop aur roshni se juda word.'),
]
active_words = {}
active_scrambles = {}
last_pairing = {}


def dm_started_notice(message):
    return is_group(message) and message.from_user and not has_started_dm(message.from_user.id)


def player_label(row):
    if row.get('username'):
        return '@' + row['username']
    return row.get('first_name') or 'Player'

async def new_couple(chat_id, announce=True):
    members = game_members(chat_id)
    if len(members) < 2:
        if announce:
            await bot.send_message(chat_id, '💞 Couple Club ke liye kam se kam 2 players chahiye. `/joincouple` se join karein.')
        return False
    random.shuffle(members)
    pairs = []
    while len(members) >= 2:
        a, b = members.pop(), members.pop()
        pct = random.randint(45, 100)
        pairs.append((a, b, pct))
    lines = ['💖 **AURAX COUPLE CLUB — NEW MATCHES** 💖', '✨ Fresh pairing is here!']
    for a, b, pct in pairs:
        bar = '💗' * (pct // 10) + '🤍' * (10 - pct // 10)
        lines.append(f'\n{player_label(a)} + {player_label(b)}\n{bar} **{pct}% match**')
    if members:
        lines.append(f"\n🌟 {player_label(members[0])} is today's VIP single — next match may be yours!")
    lines.append('\n⏰ Next automatic pairing in 6 hours. This is just for fun!')
    last_pairing[chat_id] = time.time()
    set_last_pairing(chat_id, int(last_pairing[chat_id]))
    if announce:
        await bot.send_message(chat_id, '\n'.join(lines))
    return True

@bot.on_message(filters.command('joincouple') & filters.group)
async def joincouple_cmd(_, message):
    if not message.from_user: return
    if dm_started_notice(message):
        return await message.reply_text('🔐 Pehle mujhe DM mein /start bhejiye, phir /joincouple karein.')
    save_user(message.from_user); join_game(message.chat.id, message.from_user); register_game_group(message.chat.id, message.chat.title or '')
    await message.reply_text(f'💞 {message.from_user.first_name} Couple Club mein join ho gaye! Har 6 ghante nayi pairing hogi. `/leavecouple` se opt out kar sakte hain.')

@bot.on_message(filters.command('leavecouple') & filters.group)
async def leavecouple_cmd(_, message):
    if not message.from_user: return
    leave_game(message.chat.id, message.from_user.id)
    await message.reply_text('💔 Aap Couple Club se nikal gaye. Jab chahein `/joincouple` se wapas aa sakte hain.')

@bot.on_message(filters.command('couple') & filters.group)
async def couple_cmd(_, message):
    if not message.from_user: return
    if dm_started_notice(message):
        return await message.reply_text('🔐 Pehle mujhe DM mein /start bhejiye, phir games khelein.')
    register_game_group(message.chat.id, message.chat.title or '')
    await new_couple(message.chat.id)

@bot.on_message(filters.command('love') & filters.group)
async def love_cmd(_, message):
    if not message.from_user: return
    if dm_started_notice(message):
        return await message.reply_text('🔐 Pehle mujhe DM mein /start bhejiye.')
    args = message.command[1:]
    if len(args) < 2:
        return await message.reply_text('💘 Usage: `/love @user1 @user2` — sirf fun compatibility percentage!')
    pair = '|'.join(sorted([args[0].lower(), args[1].lower()]))
    # Same names return the same fun result for consistency.
    pct = int(hashlib.sha256(pair.encode()).hexdigest()[:8], 16) % 101
    bar = '💗' * (pct // 10) + '🤍' * (10 - pct // 10)
    await message.reply_text(f'💞 **LOVE COMPATIBILITY** 💞\n{args[0]} + {args[1]}\n{bar}\n**{pct}% match!**\n_Just for fun — real relationships are not measured by a bot._')

@bot.on_message(filters.command('wordgame') & filters.group)
async def wordgame_cmd(_, message):
    if not message.from_user: return
    if dm_started_notice(message):
        return await message.reply_text('🔐 Pehle mujhe DM mein /start bhejiye, phir game khelein.')
    word, hint = random.choice(WORDS)
    active_words[message.chat.id] = {'word': word, 'hint': hint, 'tries': 0, 'started': time.time()}
    masked = ' '.join('_' for _ in word)
    await message.reply_text(f'🕵️ **HIDDEN WORD CHALLENGE**\n\nWord: `{masked}` ({len(word)} letters)\nHint: {hint}\n\nGuess bhejein: `/guess yourword`\nHint dobara dekhne ke liye `/hint`')

@bot.on_message(filters.command('guess') & filters.group)
async def guess_cmd(_, message):
    if dm_started_notice(message): return await message.reply_text('🔐 Pehle mujhe DM mein /start bhejiye.')
    game = active_words.get(message.chat.id)
    guess = ''.join(message.command[1:]).strip().upper()
    if not game:
        return await message.reply_text('🎮 Koi hidden-word game active nahi hai. `/wordgame` se shuru karein.')
    if not guess:
        return await message.reply_text('Usage: `/guess yourword`')
    game['tries'] += 1
    if guess == game['word']:
        active_words.pop(message.chat.id, None)
        await message.reply_text(f'🎉 **CORRECT!** {message.from_user.first_name if message.from_user else "Player"} ne `{guess}` sahi guess kiya! 🏆\nAttempts: {game["tries"]}')
    else:
        await message.reply_text('❌ Galat guess! Phir try karein. `/hint` se hint dekhein.')

@bot.on_message(filters.command('hint') & filters.group)
async def hint_cmd(_, message):
    if dm_started_notice(message): return await message.reply_text('🔐 Pehle mujhe DM mein /start bhejiye.')
    game = active_words.get(message.chat.id)
    if not game: return await message.reply_text('Koi game active nahi. `/wordgame` shuru karein.')
    await message.reply_text(f'💡 Hint: {game["hint"]}\nLetters: {len(game["word"])}')

@bot.on_message(filters.command('scramble') & filters.group)
async def scramble_cmd(_, message):
    if not message.from_user: return
    if dm_started_notice(message):
        return await message.reply_text('🔐 Pehle mujhe DM mein /start bhejiye.')
    word, hint = random.choice(WORDS)
    letters = list(word)
    for _ in range(5): random.shuffle(letters)
    scrambled = ''.join(letters)
    if scrambled == word and len(letters) > 1: scrambled = scrambled[1:] + scrambled[0]
    active_scrambles[message.chat.id] = {'word': word, 'hint': hint}
    await message.reply_text(f'🔤 **WORD SCRAMBLE**\nUnscramble: `{scrambled}`\nHint: {hint}\nAnswer: `/unscramble yourword`')

@bot.on_message(filters.command('unscramble') & filters.group)
async def unscramble_cmd(_, message):
    if dm_started_notice(message): return await message.reply_text('🔐 Pehle mujhe DM mein /start bhejiye.')
    game = active_scrambles.get(message.chat.id)
    guess = ''.join(message.command[1:]).strip().upper()
    if not game: return await message.reply_text('Pehle `/scramble` se game shuru karein.')
    if guess == game['word']:
        active_scrambles.pop(message.chat.id, None)
        await message.reply_text(f'🏆 Correct! Answer `{guess}` hai. Excellent!')
    else:
        await message.reply_text('❌ Not quite! Dobara try karein.')


wordchain_state = {}
RIDDLES = [
    ('I have keys but no locks, space but no room. What am I?', 'KEYBOARD'),
    ('What has a face and two hands but no arms or legs?', 'CLOCK'),
    ('What gets wetter as it dries?', 'TOWEL'),
    ('What has many teeth but cannot bite?', 'COMB'),
    ('What has to be broken before you can use it?', 'EGG'),
]
active_riddles = {}

@bot.on_message(filters.command('wordchain') & filters.group)
async def wordchain_cmd(_, message):
    if not message.from_user: return
    if dm_started_notice(message): return await message.reply_text('🔐 Pehle mujhe DM mein /start bhejiye.')
    if len(message.command) < 2:
        wordchain_state[message.chat.id] = {'last': '', 'used': set()}
        return await message.reply_text('🔗 **WORD CHAIN** shuru! `/wordchain apple` likhein. Har agla word pichhle word ke aakhri letter se shuru hona chahiye. Repeat word allowed nahi.')
    word = message.command[1].strip().lower()
    state = wordchain_state.setdefault(message.chat.id, {'last': '', 'used': set()})
    if not word.isalpha() or len(word) < 2:
        return await message.reply_text('Kam se kam 2 letters ka English word bhejein.')
    if word in state['used']:
        return await message.reply_text('🔁 Ye word pehle use ho chuka hai. Naya word try karein.')
    if state['last'] and word[0] != state['last']:
        return await message.reply_text(f'❌ Word **{state["last"]}** se shuru hona chahiye.')
    state['used'].add(word); state['last'] = word[-1]
    await message.reply_text(f'✅ **{word.upper()}** accepted! Ab **{word[-1].upper()}** se shuru hone wala word bhejein: `/wordchain {word[-1]}...`')

@bot.on_message(filters.command('riddle') & filters.group)
async def riddle_cmd(_, message):
    if not message.from_user: return
    if dm_started_notice(message): return await message.reply_text('🔐 Pehle mujhe DM mein /start bhejiye.')
    riddle, answer = random.choice(RIDDLES)
    active_riddles[message.chat.id] = answer
    await message.reply_text(f'🧠 **AURAX RIDDLE TIME**\n{riddle}\n\nAnswer: `/answer youranswer`')

@bot.on_message(filters.command('answer') & filters.group)
async def answer_cmd(_, message):
    if dm_started_notice(message): return await message.reply_text('🔐 Pehle mujhe DM mein /start bhejiye.')
    answer = active_riddles.get(message.chat.id)
    guess = ' '.join(message.command[1:]).strip().upper()
    if not answer: return await message.reply_text('Pehle `/riddle` shuru karein.')
    if guess == answer:
        active_riddles.pop(message.chat.id, None)
        await message.reply_text(f'🎉 Correct! Answer **{answer}** hai! 🏆')
    else:
        await message.reply_text('❌ Wrong answer. Ek baar aur try karein!')

async def couple_scheduler():
    # Each group receives new matches every six hours; groups need at least two opted-in players.
    while True:
        try:
            now = time.time()
            for chat_id in game_group_ids():
                if len(game_members(chat_id)) < 2: continue
                previous = get_last_pairing(chat_id)
                if now - previous >= 6 * 60 * 60:
                    await new_couple(chat_id)
                    await asyncio.sleep(0.2)
        except Exception:
            log.exception('couple scheduler error')
        await asyncio.sleep(60)


@bot.on_message(filters.command('broadcast') & filters.private)
async def broadcast_cmd(_, message):
    if not OWNER_ID or not message.from_user or message.from_user.id != OWNER_ID:
        return await message.reply_text('⛔ Owner-only command.')
    body = message.text.partition(' ')[2].strip()
    if not body: return await message.reply_text('Usage: `/broadcast your message`')
    sent = failed = 0
    for uid in all_user_ids():
        try: await bot.send_message(uid, body); sent += 1
        except Exception: failed += 1
        await asyncio.sleep(0.05)
    await message.reply_text(f'Broadcast finished. Sent: {sent}; failed: {failed}.')

async def main():
    global BOT_USERNAME
    init_db()
    await bot.start()
    try:
        await user.start()
        await calls.start()
        me = await bot.get_me()
        # Always populate the Add-to-Group button from Telegram, even if BOT_USERNAME
        # was not configured in Render.
        if me.username:
            BOT_USERNAME = me.username
        log.info('AuraX Music started as @%s', me.username)
        scheduler_task = asyncio.create_task(couple_scheduler())
        try: await asyncio.Event().wait()
        finally: scheduler_task.cancel()
    finally:
        try: await calls.stop()
        except Exception: pass
        try: await user.stop()
        except Exception: pass
        await bot.stop()

if __name__ == '__main__':
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): log.info('Stopping AuraX Music')
