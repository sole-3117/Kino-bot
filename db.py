import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    username TEXT,
    status TEXT,
    sub_until TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    year TEXT,
    genre TEXT,
    rating TEXT,
    description TEXT,
    file_id TEXT
)
""")

conn.commit()


def get_user(user_id):
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cur.fetchone()


def add_user(user_id, name, username):
    cur.execute(
        "INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?)",
        (user_id, name, username, "Expired", None)
    )
    conn.commit()


def activate_sub(user_id, days):
    until = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    cur.execute(
        "UPDATE users SET status='Active', sub_until=? WHERE user_id=?",
        (until, user_id)
    )
    conn.commit()
