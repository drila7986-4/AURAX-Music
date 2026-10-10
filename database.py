"""SQLite persistence for users, linked groups, and per-chat queues."""
import sqlite3
import os
from contextlib import closing
from config import DATABASE_PATH


def connect():
    parent = os.path.dirname(os.path.abspath(DATABASE_PATH))
    os.makedirs(parent, exist_ok=True)
    db = sqlite3.connect(DATABASE_PATH, timeout=20)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with closing(connect()) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT DEFAULT '', first_name TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS started_dm (user_id INTEGER PRIMARY KEY, started_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS links (user_id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS queues (chat_id INTEGER NOT NULL, position INTEGER NOT NULL, query TEXT NOT NULL, requested_by INTEGER NOT NULL, PRIMARY KEY(chat_id, position));
        CREATE TABLE IF NOT EXISTS game_members (chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, username TEXT DEFAULT '', first_name TEXT DEFAULT '', joined_at INTEGER NOT NULL, PRIMARY KEY(chat_id, user_id));
        CREATE TABLE IF NOT EXISTS game_groups (chat_id INTEGER PRIMARY KEY, title TEXT DEFAULT '', updated_at INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS pairing_state (chat_id INTEGER PRIMARY KEY, last_pair_at INTEGER NOT NULL DEFAULT 0);
        """)
        db.commit()


def save_user(user):
    if not user: return
    with closing(connect()) as db:
        db.execute("INSERT INTO users(user_id, username, first_name) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name", (user.id, user.username or '', user.first_name or ''))
        db.commit()


def all_user_ids():
    with closing(connect()) as db:
        return [r['user_id'] for r in db.execute('SELECT user_id FROM users')]


def link_group(user_id, chat_id):
    with closing(connect()) as db:
        db.execute('INSERT INTO links(user_id, chat_id) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET chat_id=excluded.chat_id', (user_id, chat_id)); db.commit()


def get_linked_group(user_id):
    with closing(connect()) as db:
        row = db.execute('SELECT chat_id FROM links WHERE user_id=?', (user_id,)).fetchone()
        return row['chat_id'] if row else None


def enqueue(chat_id, query, requested_by):
    with closing(connect()) as db:
        row = db.execute('SELECT COALESCE(MAX(position), 0)+1 AS n FROM queues WHERE chat_id=?', (chat_id,)).fetchone()
        pos = row['n']; db.execute('INSERT INTO queues(chat_id, position, query, requested_by) VALUES(?,?,?,?)', (chat_id, pos, query, requested_by)); db.commit(); return pos


def queue_items(chat_id):
    with closing(connect()) as db:
        return [dict(r) for r in db.execute('SELECT position, query, requested_by FROM queues WHERE chat_id=? ORDER BY position', (chat_id,))]


def pop_next(chat_id):
    with closing(connect()) as db:
        row = db.execute('SELECT position, query, requested_by FROM queues WHERE chat_id=? ORDER BY position LIMIT 1', (chat_id,)).fetchone()
        if not row: return None
        db.execute('DELETE FROM queues WHERE chat_id=? AND position=?', (chat_id, row['position']))
        db.execute('UPDATE queues SET position=position-1 WHERE chat_id=? AND position>?', (chat_id, row['position']))
        db.commit(); return dict(row)


def clear_queue(chat_id):
    with closing(connect()) as db:
        db.execute('DELETE FROM queues WHERE chat_id=?', (chat_id,)); db.commit()


def mark_started_dm(user_id):
    import time
    with closing(connect()) as db:
        db.execute('INSERT INTO started_dm(user_id, started_at) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET started_at=excluded.started_at', (user_id, int(time.time())))
        db.commit()


def has_started_dm(user_id):
    with closing(connect()) as db:
        return db.execute('SELECT 1 FROM started_dm WHERE user_id=?', (user_id,)).fetchone() is not None


def register_game_group(chat_id, title=''):
    import time
    with closing(connect()) as db:
        db.execute('INSERT INTO game_groups(chat_id,title,updated_at) VALUES(?,?,?) ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title, updated_at=excluded.updated_at', (chat_id, title or '', int(time.time())))
        db.commit()


def join_game(chat_id, user):
    import time
    if not user: return
    with closing(connect()) as db:
        db.execute('INSERT INTO game_members(chat_id,user_id,username,first_name,joined_at) VALUES(?,?,?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name', (chat_id, user.id, user.username or '', user.first_name or 'Player', int(time.time())))
        db.execute('INSERT INTO game_groups(chat_id,title,updated_at) VALUES(?,?,?) ON CONFLICT(chat_id) DO UPDATE SET updated_at=excluded.updated_at', (chat_id, '', int(time.time())))
        db.commit()


def leave_game(chat_id, user_id):
    with closing(connect()) as db:
        db.execute('DELETE FROM game_members WHERE chat_id=? AND user_id=?', (chat_id, user_id)); db.commit()


def game_members(chat_id):
    with closing(connect()) as db:
        return [dict(r) for r in db.execute('SELECT user_id,username,first_name FROM game_members WHERE chat_id=? ORDER BY joined_at', (chat_id,))]


def game_group_ids():
    with closing(connect()) as db:
        return [r['chat_id'] for r in db.execute('SELECT chat_id FROM game_groups')]


def get_last_pairing(chat_id):
    with closing(connect()) as db:
        row = db.execute('SELECT last_pair_at FROM pairing_state WHERE chat_id=?', (chat_id,)).fetchone()
        return int(row['last_pair_at']) if row else 0


def set_last_pairing(chat_id, timestamp):
    with closing(connect()) as db:
        db.execute('INSERT INTO pairing_state(chat_id,last_pair_at) VALUES(?,?) ON CONFLICT(chat_id) DO UPDATE SET last_pair_at=excluded.last_pair_at', (chat_id, int(timestamp)))
        db.commit()
