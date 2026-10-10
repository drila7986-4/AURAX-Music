"""AuraX music playback. YouTube is the audio transport; other provider links resolve to metadata/search where possible."""
import asyncio
import logging
import re
import time
from urllib.parse import urlparse

import requests
from yt_dlp import YoutubeDL
from pytgcalls.types import MediaStream
from database import enqueue, queue_items, pop_next, clear_queue
from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

log = logging.getLogger(__name__)
YTDLP_OPTIONS = {
    'format': 'bestaudio/best', 'quiet': True, 'no_warnings': True,
    'noplaylist': True, 'default_search': 'ytsearch1', 'source_address': '0.0.0.0',
    'socket_timeout': 20, 'retries': 2,
}
SPOTIFY_TRACK = re.compile(r'https?://open\.spotify\.com/(?:intl-[^/]+/)?track/([A-Za-z0-9]+)')
SAAVN_URL = re.compile(r'https?://(?:www\.)?jiosaavn\.com/', re.I)
GAANA_URL = re.compile(r'https?://(?:www\.)?gaana\.com/', re.I)


def spotify_track_title(url: str) -> str:
    match = SPOTIFY_TRACK.search(url)
    if not match:
        return url
    if not (SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET):
        raise RuntimeError('Spotify track link detected. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in Render Environment.')
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    client = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))
    track = client.track(match.group(1))
    artists = ', '.join(a['name'] for a in track.get('artists', []))
    return f"{track.get('name', '')} {artists}".strip()


def page_title(url: str) -> str:
    """Read a provider page title as a fallback; never treats a web page URL as audio."""
    try:
        response = requests.get(url, timeout=12, headers={'User-Agent': 'Mozilla/5.0 (compatible; AuraXMusic/1.0)'})
        response.raise_for_status()
        html = response.text[:1_000_000]
        # Prefer OpenGraph title, then standard title. Avoid adding a parsing dependency.
        for pattern in (
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']',
            r'<title[^>]*>(.*?)</title>',
        ):
            match = re.search(pattern, html, re.I | re.S)
            if match:
                title = re.sub(r'\s+', ' ', match.group(1)).strip()
                title = re.sub(r'\s*[-|–]\s*(JioSaavn|Gaana).*$','',title,flags=re.I).strip()
                if title and title.lower() not in ('jiosaavn', 'gaana'):
                    return title
    except Exception as exc:
        log.info('Could not read provider page metadata (%s): %s', urlparse(url).netloc, exc)
    return ''


def normalize_query(query: str) -> str:
    query = query.strip()
    query = spotify_track_title(query)
    if SAAVN_URL.match(query) or GAANA_URL.match(query):
        title = page_title(query)
        if title:
            return title
        # Try the site's own extractor if the installed yt-dlp version supports it.
        try:
            with YoutubeDL({**YTDLP_OPTIONS, 'extract_flat': True}) as ydl:
                info = ydl.extract_info(query, download=False)
                if info and info.get('title'):
                    return info['title']
        except Exception as exc:
            log.info('Provider extractor unavailable for %s: %s', urlparse(query).netloc, exc)
        raise ValueError('Could not read this JioSaavn/Gaana link. Send the song name and artist instead.')
    return query


def resolve_audio(query: str):
    """Find a song on YouTube, resolve the selected video's direct audio URL, and return it.

    Searching and resolving are separate steps: yt-dlp search entries often contain a
    watch-page URL, not a stream URL that FFmpeg can consume directly.
    """
    normalized = normalize_query(query)
    is_provider_page = bool(
        SPOTIFY_TRACK.search(query) or SAAVN_URL.match(query) or GAANA_URL.match(query)
    )
    is_url = normalized.startswith(("http://", "https://")) and not is_provider_page

    options = dict(YTDLP_OPTIONS)
    with YoutubeDL(options) as ydl:
        if is_url:
            candidates = [normalized]
        else:
            # Search several results so a removed, blocked, or non-audio result doesn't
            # prevent playback when another matching YouTube upload is available.
            search = ydl.extract_info(f"ytsearch5:{normalized}", download=False)
            entries = (search or {}).get("entries") or []
            candidates = []
            for entry in entries:
                if not entry:
                    continue
                video_url = entry.get("webpage_url") or entry.get("original_url")
                if not video_url:
                    raw_url = entry.get("url")
                    video_id = entry.get("id")
                    if raw_url and str(raw_url).startswith(("http://", "https://")):
                        video_url = raw_url
                    elif video_id:
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                if video_url and video_url not in candidates:
                    candidates.append(video_url)
            if not candidates:
                raise ValueError(f'No YouTube results found for "{normalized}". Try another song name.')

        errors = []
        for video_url in candidates:
            try:
                info = ydl.extract_info(video_url, download=False)
                if info and info.get("entries"):
                    info = next((entry for entry in info["entries"] if entry), None)
                if not info:
                    continue
                # Resolve direct audio stream URL (not the YouTube watch page URL).
                audio_url = info.get("url")
                if not audio_url:
                    formats = info.get("formats") or []
                    audio_formats = [f for f in formats if f.get("url") and f.get("acodec") != "none"]
                    if audio_formats:
                        audio_url = audio_formats[-1]["url"]
                if not audio_url:
                    continue
                title = info.get("title") or normalized
                duration = int(info.get("duration") or 0)
                log.info("Resolved YouTube audio: %s (%ss)", title, duration or "unknown duration")
                return audio_url, title, duration
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
                log.warning("Could not resolve YouTube result %s: %s", video_url, exc)

    detail = errors[-1] if errors else "No result exposed a playable audio stream"
    raise ValueError(f'Could not resolve playable YouTube audio for "{normalized}". {detail}')


class MusicManager:
    def __init__(self, calls):
        self.calls = calls
        self.current = {}
        self.locks = {}
        self.end_tasks = {}
        self.volumes = {}
        self.offsets = {}
        self.started_at = {}
        self.paused_at = {}
        self.paused_total = {}
        self.loop_modes = {}  # per-chat repeat-current-track mode

    def _lock(self, chat_id):
        if chat_id not in self.locks:
            self.locks[chat_id] = asyncio.Lock()
        return self.locks[chat_id]

    def _cancel_end_task(self, chat_id):
        task = self.end_tasks.pop(chat_id, None)
        if task and not task.done() and task is not asyncio.current_task():
            task.cancel()

    def _schedule_end(self, chat_id, duration):
        self._cancel_end_task(chat_id)
        if duration > 0:
            self.end_tasks[chat_id] = asyncio.create_task(self._auto_advance(chat_id, duration))

    async def _auto_advance(self, chat_id, duration):
        try:
            await asyncio.sleep(max(1, duration))
            # If playback was paused, wait for it to resume before consuming the remaining time.
            while chat_id in self.paused_at:
                await asyncio.sleep(1)
            if self.loop_modes.get(chat_id, False) and chat_id in self.current:
                async with self._lock(chat_id):
                    current = self.current.get(chat_id)
                    if current:
                        await self._start_track(chat_id, current['query'], current['requested_by'])
            else:
                await self.next_track(chat_id)
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception('Automatic queue advance failed for %s', chat_id)

    async def _start_track(self, chat_id, query, requested_by, offset=0):
        url, title, duration = await asyncio.to_thread(resolve_audio, query)
        ffmpeg_parameters = f'-ss {int(offset)}' if offset > 0 else ''
        stream = MediaStream(url, ffmpeg_parameters=ffmpeg_parameters) if ffmpeg_parameters else MediaStream(url)
        await self.calls.play(chat_id, stream)
        self.current[chat_id] = {
            'query': query, 'title': title, 'requested_by': requested_by,
            'duration': duration, 'url': url,
        }
        self.offsets[chat_id] = int(offset)
        self.started_at[chat_id] = time.monotonic()
        self.paused_total[chat_id] = 0
        self._schedule_end(chat_id, max(0, duration - offset))
        return title

    async def play(self, chat_id: int, query: str, requested_by: int):
        async with self._lock(chat_id):
            if chat_id in self.current:
                pos = enqueue(chat_id, query, requested_by)
                return f'➕ Added to queue at position {pos}.'
            title = await self._start_track(chat_id, query, requested_by)
            return f'▶️ Playing in VC: **{title}**'

    async def next_track(self, chat_id: int):
        async with self._lock(chat_id):
            self._cancel_end_task(chat_id)
            while True:
                item = pop_next(chat_id)
                if not item:
                    self.current.pop(chat_id, None)
                    self.offsets.pop(chat_id, None)
                    self.started_at.pop(chat_id, None)
                    self.paused_at.pop(chat_id, None)
                    return False
                try:
                    await self._start_track(chat_id, item['query'], item['requested_by'])
                    return True
                except Exception:
                    log.exception('Could not start queued item; trying next queued item')

    def queue_text(self, chat_id: int):
        items = queue_items(chat_id)
        return '\n'.join(f"{i}. {item['query']}" for i, item in enumerate(items, 1)) if items else 'Queue is empty.'

    def elapsed(self, chat_id: int) -> int:
        if chat_id not in self.current:
            return 0
        if chat_id in self.paused_at:
            return int(self.paused_at[chat_id] - self.started_at.get(chat_id, self.paused_at[chat_id]) + self.offsets.get(chat_id, 0) - self.paused_total.get(chat_id, 0))
        return max(0, int(time.monotonic() - self.started_at.get(chat_id, time.monotonic()) + self.offsets.get(chat_id, 0) - self.paused_total.get(chat_id, 0)))

    async def pause(self, chat_id):
        await self.calls.pause(chat_id)
        self.paused_at[chat_id] = time.monotonic()
        self._cancel_end_task(chat_id)

    async def resume(self, chat_id):
        await self.calls.resume(chat_id)
        if chat_id in self.paused_at:
            self.paused_total[chat_id] = self.paused_total.get(chat_id, 0) + (time.monotonic() - self.paused_at.pop(chat_id))
        current = self.current.get(chat_id, {})
        remaining = max(0, int(current.get('duration', 0) - self.elapsed(chat_id)))
        self._schedule_end(chat_id, remaining)

    async def seek(self, chat_id, seconds):
        current = self.current.get(chat_id)
        if not current:
            raise RuntimeError('Nothing is playing.')
        duration = int(current.get('duration') or 0)
        seconds = max(0, int(seconds))
        if duration:
            seconds = min(seconds, max(0, duration - 3))
        self._cancel_end_task(chat_id)
        await self.calls.play(chat_id, MediaStream(current['url'], ffmpeg_parameters=f'-ss {seconds}'))
        self.offsets[chat_id] = seconds
        self.started_at[chat_id] = time.monotonic()
        self.paused_total[chat_id] = 0
        self.paused_at.pop(chat_id, None)
        self._schedule_end(chat_id, max(0, duration - seconds))

    async def set_speed(self, chat_id: int, speed: float):
        current = self.current.get(chat_id)
        if not current:
            raise RuntimeError('Nothing is playing.')
        if not 0.5 <= speed <= 2.0:
            raise ValueError('Speed must be between 0.5 and 2.0.')
        elapsed = self.elapsed(chat_id)
        self._cancel_end_task(chat_id)
        # -atmid separates ffmpeg input and output options in PyTgCalls.
        params = f'-ss {elapsed} -atmid -filter:a atempo={speed:g}'
        await self.calls.play(chat_id, MediaStream(current['url'], ffmpeg_parameters=params))
        self.offsets[chat_id] = elapsed
        self.started_at[chat_id] = time.monotonic()
        self.paused_total[chat_id] = 0
        self.paused_at.pop(chat_id, None)
        self._schedule_end(chat_id, max(0, int(current.get('duration') or 0) - elapsed))

    async def stop(self, chat_id: int):
        self._cancel_end_task(chat_id)
        await self.calls.leave_call(chat_id)
        self.current.pop(chat_id, None)
        self.offsets.pop(chat_id, None)
        self.started_at.pop(chat_id, None)
        self.paused_at.pop(chat_id, None)
        self.paused_total.pop(chat_id, None)
        self.loop_modes.pop(chat_id, None)
        clear_queue(chat_id)
