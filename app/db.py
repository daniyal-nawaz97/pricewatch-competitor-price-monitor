import hashlib
import json
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import DB_PATH

_lock = threading.RLock()
_conn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer', password_hash TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, sku TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
    brand TEXT, category TEXT, price REAL NOT NULL, cost REAL, image TEXT, top INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS own_prices (product_id INTEGER NOT NULL, day TEXT NOT NULL, price REAL NOT NULL, PRIMARY KEY (product_id, day));
CREATE TABLE IF NOT EXISTS competitors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, website TEXT, color TEXT,
    price_selector TEXT, stock_selector TEXT, catalog_url TEXT, is_demo INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS listings (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, competitor_id INTEGER NOT NULL,
    url TEXT NOT NULL, title TEXT, status TEXT NOT NULL DEFAULT 'confirmed', confidence REAL, created_at TEXT NOT NULL,
    UNIQUE (competitor_id, url));
CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id INTEGER NOT NULL, day TEXT NOT NULL,
    checked_at TEXT NOT NULL, ok INTEGER NOT NULL, price REAL, regular_price REAL, in_stock INTEGER, error TEXT, source TEXT,
    UNIQUE (listing_id, day));
CREATE INDEX IF NOT EXISTS idx_obs_day ON observations(day);
CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
    pages INTEGER DEFAULT 0, ok INTEGER DEFAULT 0, failed INTEGER DEFAULT 0, changes INTEGER DEFAULT 0, trigger TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, created_at TEXT NOT NULL, type TEXT NOT NULL,
    product_id INTEGER, competitor_id INTEGER, listing_id INTEGER, old_price REAL, new_price REAL, message TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info', is_read INTEGER NOT NULL DEFAULT 0, delivered TEXT);
CREATE INDEX IF NOT EXISTS idx_alerts_day ON alerts(day);
CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, day TEXT NOT NULL, title TEXT NOT NULL,
    summary_json TEXT, html_path TEXT, pdf_path TEXT, xlsx_path TEXT, sent_to TEXT, created_at TEXT NOT NULL, UNIQUE (kind, day));
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

DEFAULT_SETTINGS = {
    "company_name": "GadgetHub.pk",
    "accent_color": "#4f46e5",
    "logo_url": "",
    "currency": "PKR",
    "rounding": 0,                      # decimals shown for prices
    "check_time": "07:00",              # daily collection (server local time)
    "report_time": "08:00",
    "daily_recipients": ["owner@gadgethub.example"],
    "weekly_recipients": ["owner@gadgethub.example", "pricing@gadgethub.example"],
    "weekly_day": "Monday",
    "rules": {
        "cheaper_than_you_pct": 5, "price_drop_pct": 5, "price_increase_pct": 10,
        "top_out_of_stock": True, "back_in_stock": True, "new_product": True,
    },
    "channels": {"in_app": True, "email": True, "telegram": False, "whatsapp": False},
    "telegram_chat_id": "",
    "whatsapp_to": "",
    "demo_anchor": "",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def tx():
    global _conn
    with _lock:
        if _conn is None:
            _conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield _conn
            _conn.commit()
        except Exception:
            _conn.rollback()
            raise


def query(sql, params=()):
    with tx() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def one(sql, params=()):
    r = query(sql, params)
    return r[0] if r else None


def execute(sql, params=()):
    with tx() as c:
        return c.execute(sql, params).lastrowid


def many(sql, rows):
    with tx() as c:
        c.executemany(sql, rows)


def hash_password(pw, salt=None):
    salt = salt or secrets.token_hex(8)
    return f"{salt}${hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 120_000).hex()}"


def check_password(pw, stored):
    if not stored or "$" not in stored:
        return False
    return secrets.compare_digest(hash_password(pw, stored.split("$", 1)[0]), stored)


def get_settings():
    out = json.loads(json.dumps(DEFAULT_SETTINGS))
    for r in query("SELECT key, value FROM settings"):
        out[r["key"]] = json.loads(r["value"])
    return out


def set_settings(values: dict):
    with tx() as c:
        for k, v in values.items():
            if k in DEFAULT_SETTINGS:
                c.execute("INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, json.dumps(v)))


def init_schema():
    with tx() as c:
        c.executescript(SCHEMA)
