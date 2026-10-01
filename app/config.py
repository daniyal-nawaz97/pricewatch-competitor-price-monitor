import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

APP_NAME = os.getenv("APP_NAME", "PriceWatch")
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
REPORTS_DIR = DATA_DIR / "reports"
BRAND_DIR = DATA_DIR / "brand"
DB_PATH = DATA_DIR / "pricewatch.db"
STATIC_DIR = BASE_DIR / "static"

# Public URL of this app (used for links in emails). The demo competitor shops are served by the app itself.
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
PORT = int(os.getenv("PORT", "8003"))
SELF_URL = os.getenv("SELF_URL", f"http://127.0.0.1:{PORT}").rstrip("/")  # how the collector reaches the demo shops

DEMO_EMAIL = os.getenv("DEMO_EMAIL", "demo@pricewatch.app")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo1234")
DEMO_HISTORY_DAYS = int(os.getenv("DEMO_HISTORY_DAYS", "60"))
# Real client install: DEMO_MODE=0 skips the demo store and creates this admin account on first start
DEMO_MODE = os.getenv("DEMO_MODE", "1") != "0"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()

# Collector etiquette: identify ourselves and go slowly on every website
USER_AGENT = os.getenv("USER_AGENT", "PriceWatchBot/1.0 (+price monitoring; contact the site owner's client)")
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY_SECONDS", "1.5"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "20"))

# Delivery channels (all optional; in-app alerts and the report outbox always work)
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "reports@pricewatch.local")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "").strip()
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "").strip()

CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "").strip()
CONTACT_WHATSAPP = os.getenv("CONTACT_WHATSAPP", "").strip()
MANUAL_SECONDS_PER_CHECK = float(os.getenv("MANUAL_SECONDS_PER_CHECK", "45"))  # checking one competitor price by hand

for d in (REPORTS_DIR, BRAND_DIR):
    d.mkdir(parents=True, exist_ok=True)
