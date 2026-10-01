"""Create the demo store: products, three fictitious competitors, listings, and back-filled history.

History before today is generated with the same simulation the demo shops use and is stored with source='demo-backfill'.
Today's prices are then collected live over HTTP by the real collector.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from . import alerts, db, demo, matching, reports
from .config import DEMO_EMAIL, DEMO_HISTORY_DAYS, DEMO_PASSWORD

log = logging.getLogger("pricewatch.seed")


def seed_demo(anchor: date | None = None):
    db.init_schema()
    if db.one("SELECT id FROM products LIMIT 1"):
        return False
    anchor = anchor or date.today()
    now = db.now()
    for email, name, role, pw in [(DEMO_EMAIL, "Demo Owner", "admin", DEMO_PASSWORD), ("pricing@gadgethub.example", "Hamza Riaz", "analyst", None),
                                  ("store@gadgethub.example", "Sana Iqbal", "viewer", None)]:
        db.execute("INSERT OR IGNORE INTO users(email, name, role, password_hash, created_at) VALUES(?,?,?,?,?)",
                   (email, name, role, db.hash_password(pw) if pw else None, now))
    db.set_settings({"demo_anchor": anchor.isoformat()})
    for p in demo.own_catalog():
        db.execute("INSERT INTO products(sku, name, brand, category, price, cost, top, created_at) VALUES(?,?,?,?,?,?,?,?)",
                   (p["sku"], p["name"], p["brand"], p["category"], demo.own_price(p["sku"], p["price"], anchor, anchor), p["cost"], p["top"], now))
    products = db.query("SELECT * FROM products")
    for c in demo.COMPETITORS:
        cid = db.execute("INSERT INTO competitors(name, website, color, price_selector, stock_selector, catalog_url, is_demo, created_at) VALUES(?,?,?,?,?,?,1,?)",
                         (c["name"], f"/demo-shops/{c['slug']}/", c["color"], c.get("price_selector"), c.get("stock_selector"), f"/demo-shops/{c['slug']}/", now))
        for p in products:
            if demo.offer(c["slug"], p["sku"], anchor - timedelta(days=1), anchor) is None:
                continue
            title = demo.competitor_title(c["slug"], p["name"])
            s = matching.score(p["name"], title)
            db.execute("INSERT INTO listings(product_id, competitor_id, url, title, status, confidence, created_at) VALUES(?,?,?,?,?,?,?)",
                       (p["id"], cid, f"/demo-shops/{c['slug']}/p/{demo.handle(title)}", title, "confirmed" if s >= 0.8 else "pending", s, now))
    # history
    listings = db.query("SELECT l.id, l.product_id, l.status, p.sku, c.name FROM listings l JOIN products p ON p.id=l.product_id JOIN competitors c ON c.id=l.competitor_id")
    slug = {c["name"]: c["slug"] for c in demo.COMPETITORS}
    base_price = {p["sku"]: p["price"] for p in demo.own_catalog()}
    for n in range(DEMO_HISTORY_DAYS, 0, -1):
        d = anchor - timedelta(days=n)
        rows = []
        for l in listings:
            o = demo.offer(slug[l["name"]], l["sku"], d, anchor)
            if o:
                rows.append((l["id"], d.isoformat(), f"{d.isoformat()}T07:0{n % 10}:00+00:00", 1, o[0], o[1], int(o[2]), None, "demo-backfill"))
        db.many("INSERT OR IGNORE INTO observations(listing_id, day, checked_at, ok, price, regular_price, in_stock, error, source) VALUES(?,?,?,?,?,?,?,?,?)", rows)
        db.many("INSERT OR REPLACE INTO own_prices(product_id, day, price) VALUES(?,?,?)",
                [(p["id"], d.isoformat(), demo.own_price(p["sku"], base_price[p["sku"]], d, anchor)) for p in products])
        db.execute("INSERT INTO runs(day, started_at, finished_at, pages, ok, failed, changes, trigger, status) VALUES(?,?,?,?,?,?,?,?,?)",
                   (d.isoformat(), f"{d.isoformat()}T07:00:00+00:00", f"{d.isoformat()}T07:03:00+00:00", len(rows), len(rows), 0, 0, "demo-backfill", "done"))
        changes = alerts.evaluate(d.isoformat(), deliver=False)
        db.execute("UPDATE runs SET changes=? WHERE day=? AND trigger='demo-backfill'", (changes, d.isoformat()))
    db.many("INSERT OR REPLACE INTO own_prices(product_id, day, price) VALUES(?,?,?)",
            [(p["id"], anchor.isoformat(), p["price"]) for p in products])
    db.execute("UPDATE alerts SET is_read=1, delivered='demo' WHERE day<?", ((anchor - timedelta(days=2)).isoformat(),))
    for n in range(7, 0, -1):
        reports.build_daily((anchor - timedelta(days=n)).isoformat())
    for n in range(1, 29):
        d = anchor - timedelta(days=n)
        if d.strftime("%A") == db.get_settings().get("weekly_day", "Monday"):
            reports.build_weekly(d.isoformat())
    db.execute("UPDATE reports SET sent_to='demo (not sent)'")
    log.info("Demo store created with %d days of history", DEMO_HISTORY_DAYS)
    return True
