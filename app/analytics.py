"""Where you stand: daily snapshots, trends, product histories and data health."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from . import db


def _day(d) -> str:
    return d if isinstance(d, str) else d.isoformat()


def own_price_map(day: str) -> dict[int, float]:
    rows = db.query("SELECT p.id, COALESCE((SELECT o.price FROM own_prices o WHERE o.product_id=p.id AND o.day<=? ORDER BY o.day DESC LIMIT 1), p.price) AS price "
                    "FROM products p WHERE p.active=1", (day,))
    return {r["id"]: r["price"] for r in rows}


def snapshot(day: str) -> list[dict]:
    """One row per product: your price and every competitor's latest price (within 3 days) on this day."""
    since = (date.fromisoformat(day) - timedelta(days=3)).isoformat()
    products = db.query("SELECT * FROM products WHERE active=1 ORDER BY category, name")
    own = own_price_map(day)
    comps = db.query("SELECT id, name, color FROM competitors WHERE active=1 ORDER BY id")
    obs = db.query("""SELECT l.product_id, l.competitor_id, l.url, l.id AS listing_id, o.price, o.regular_price, o.in_stock, o.day, o.checked_at
                      FROM listings l JOIN observations o ON o.listing_id=l.id
                      WHERE l.status='confirmed' AND o.ok=1 AND o.day<=? AND o.day>=?
                      ORDER BY o.day""", (day, since))
    latest = {}
    for o in obs:
        latest[(o["product_id"], o["competitor_id"])] = o
    tracked = {(r["product_id"], r["competitor_id"]) for r in db.query("SELECT product_id, competitor_id FROM listings WHERE status='confirmed'")}
    rows = []
    for p in products:
        mine = own[p["id"]]
        cells, prices_in_stock = {}, []
        for c in comps:
            o = latest.get((p["id"], c["id"]))
            if o:
                cells[c["id"]] = {"price": o["price"], "regular_price": o["regular_price"], "in_stock": bool(o["in_stock"]), "url": o["url"],
                                  "day": o["day"], "listing_id": o["listing_id"]}
                if o["in_stock"]:
                    prices_in_stock.append(o["price"])
            else:
                cells[c["id"]] = {"tracked": (p["id"], c["id"]) in tracked}
        cheapest = min(prices_in_stock) if prices_in_stock else None
        if cheapest is None:
            position, rank = "untracked", None
        else:
            rank = 1 + sum(1 for x in prices_in_stock if x < mine)
            position = "cheapest" if mine <= cheapest else "most_expensive" if mine > max(prices_in_stock) else "middle"
        rows.append({"id": p["id"], "sku": p["sku"], "name": p["name"], "brand": p["brand"], "category": p["category"], "top": bool(p["top"]),
                     "price": mine, "cost": p["cost"], "competitors": cells, "cheapest": cheapest,
                     "gap": None if cheapest is None else mine - cheapest, "gap_pct": None if cheapest is None else (mine - cheapest) / cheapest * 100,
                     "position": position, "rank": rank, "of": len(prices_in_stock) + 1 if cheapest is not None else None,
                     "market_avg": sum(prices_in_stock) / len(prices_in_stock) if prices_in_stock else None})
    return rows


def changes_on(day: str) -> list[dict]:
    """Every competitor price change observed on this day vs their previous observation."""
    prev_day = db.one("SELECT MAX(day) AS d FROM observations WHERE day<? AND ok=1", (day,))["d"]
    if not prev_day:
        return []
    rows = db.query("""SELECT o.listing_id, o.price, o.in_stock, p.price AS prev_price, p.in_stock AS prev_stock, l.product_id, l.competitor_id,
                              pr.name AS product, pr.sku, c.name AS competitor, c.color
                       FROM observations o JOIN observations p ON p.listing_id=o.listing_id AND p.day=?
                       JOIN listings l ON l.id=o.listing_id JOIN products pr ON pr.id=l.product_id JOIN competitors c ON c.id=l.competitor_id
                       WHERE o.day=? AND o.ok=1 AND p.ok=1 AND l.status='confirmed'""", (prev_day, day))
    out = []
    for r in rows:
        if r["price"] != r["prev_price"]:
            r["pct"] = (r["price"] - r["prev_price"]) / r["prev_price"] * 100
            out.append(r)
    out.sort(key=lambda r: -abs(r["pct"]))
    return out


def overview(day: str) -> dict:
    snap = snapshot(day)
    tracked = [r for r in snap if r["position"] != "untracked"]
    stand = defaultdict(int)
    for r in tracked:
        stand[r["position"]] += 1
    changes = changes_on(day)
    oos = db.one("""SELECT COUNT(*) AS n FROM observations o JOIN listings l ON l.id=o.listing_id
                    WHERE o.day=? AND o.ok=1 AND o.in_stock=0 AND l.status='confirmed'""", (day,))["n"]
    cheaper = sum(1 for r in tracked if r["cheapest"] is not None and r["cheapest"] < r["price"])
    return {
        "day": day,
        "cards": {"tracked": len(snap), "changes_today": len(changes), "competitor_cheaper": cheaper, "competitor_oos": oos,
                  "listings": db.one("SELECT COUNT(*) AS n FROM listings WHERE status='confirmed'")["n"]},
        "stand": {k: stand.get(k, 0) for k in ("cheapest", "middle", "most_expensive")}, "stand_total": len(tracked),
        "biggest_changes": [{k: c[k] for k in ("product_id", "product", "competitor", "color", "prev_price", "price", "pct")} for c in changes[:8]],
        "trend": trend(day, 30),
    }


def trend(day: str, days: int = 30) -> list[dict]:
    end = date.fromisoformat(day)
    start = end - timedelta(days=days - 1)
    obs = db.query("""SELECT o.day, l.product_id, AVG(o.price) AS avg_price FROM observations o JOIN listings l ON l.id=o.listing_id
                      WHERE o.ok=1 AND o.in_stock=1 AND l.status='confirmed' AND o.day BETWEEN ? AND ? GROUP BY o.day, l.product_id""",
                   (start.isoformat(), day))
    by_day = defaultdict(dict)
    for o in obs:
        by_day[o["day"]][o["product_id"]] = o["avg_price"]
    out = []
    for i in range(days):
        d = (start + timedelta(days=i)).isoformat()
        market = by_day.get(d)
        if not market:
            out.append({"day": d, "you": None, "market": None, "index": None})
            continue
        own = own_price_map(d)
        pids = [pid for pid in market if pid in own]
        you = sum(own[p] for p in pids) / len(pids)
        mk = sum(market[p] for p in pids) / len(pids)
        out.append({"day": d, "you": round(you, 1), "market": round(mk, 1), "index": round(100 * you / mk, 1)})
    return out


def product_detail(pid: int, day: str, days: int = 30) -> dict | None:
    p = db.one("SELECT * FROM products WHERE id=?", (pid,))
    if not p:
        return None
    end = date.fromisoformat(day)
    start = (end - timedelta(days=days - 1)).isoformat()
    comps = db.query("SELECT id, name, color, website FROM competitors ORDER BY id")
    listings = db.query("SELECT * FROM listings WHERE product_id=? AND status='confirmed'", (pid,))
    series = []
    for l in listings:
        c = next((c for c in comps if c["id"] == l["competitor_id"]), None)
        pts = db.query("SELECT day, price, regular_price, in_stock, ok, checked_at, error FROM observations WHERE listing_id=? AND day BETWEEN ? AND ? ORDER BY day",
                       (l["id"], start, day))
        last = db.one("SELECT * FROM observations WHERE listing_id=? AND day<=? ORDER BY day DESC LIMIT 1", (l["id"], day))
        last_ok = db.one("SELECT * FROM observations WHERE listing_id=? AND ok=1 AND day<=? ORDER BY day DESC LIMIT 1", (l["id"], day))
        series.append({"competitor_id": c["id"], "competitor": c["name"], "color": c["color"], "url": l["url"], "title": l["title"],
                       "points": [{"day": x["day"], "price": x["price"] if x["ok"] else None, "in_stock": x["in_stock"]} for x in pts],
                       "current": last_ok["price"] if last_ok else None, "regular_price": last_ok["regular_price"] if last_ok else None,
                       "in_stock": bool(last_ok["in_stock"]) if last_ok else None, "last_checked": last["checked_at"] if last else None,
                       "last_ok": bool(last["ok"]) if last else None, "error": last["error"] if last and not last["ok"] else None})
    own_hist = db.query("SELECT day, price FROM own_prices WHERE product_id=? ORDER BY day", (pid,))
    own_pts = []
    for i in range(days):
        d = (end - timedelta(days=days - 1 - i)).isoformat()
        prior = [o["price"] for o in own_hist if o["day"] <= d]
        own_pts.append({"day": d, "price": prior[-1] if prior else p["price"]})
    mine = own_pts[-1]["price"]
    # timeline of changes (all time, newest first)
    timeline = []
    for l in listings:
        c = next(c for c in comps if c["id"] == l["competitor_id"])
        pts = db.query("SELECT day, price, in_stock FROM observations WHERE listing_id=? AND ok=1 AND day<=? ORDER BY day", (l["id"], day))
        for a, b in zip(pts, pts[1:]):
            if a["price"] != b["price"]:
                timeline.append({"day": b["day"], "competitor": c["name"], "color": c["color"], "type": "price", "from": a["price"], "to": b["price"]})
            if a["in_stock"] != b["in_stock"]:
                timeline.append({"day": b["day"], "competitor": c["name"], "color": c["color"], "type": "stock", "in_stock": bool(b["in_stock"])})
    own_series = db.query("SELECT day, price FROM own_prices WHERE product_id=? AND day<=? ORDER BY day", (pid, day))
    for a, b in zip(own_series, own_series[1:]):
        if a["price"] != b["price"]:
            timeline.append({"day": b["day"], "competitor": "You", "color": "#111827", "type": "price", "from": a["price"], "to": b["price"]})
    timeline.sort(key=lambda t: t["day"], reverse=True)
    # plain-language insight: how long above / below market average
    snap_days = []
    for i in range(min(days, 30)):
        d = (end - timedelta(days=i)).isoformat()
        prices = [s_pt["price"] for s in series for s_pt in s["points"] if s_pt["day"] == d and s_pt["price"] and s_pt["in_stock"]]
        if prices:
            own_d = next(o["price"] for o in own_pts if o["day"] == d)
            snap_days.append(own_d > sum(prices) / len(prices))
    streak = 0
    for above in snap_days:
        if above == (snap_days[0] if snap_days else False):
            streak += 1
        else:
            break
    current = [s["current"] for s in series if s["current"] and s["in_stock"]]
    insight = None
    if snap_days:
        insight = (f"You have been above the market average for {streak} day{'s' if streak != 1 else ''}." if snap_days[0]
                   else f"You have been at or below the market average for {streak} day{'s' if streak != 1 else ''}.")
    suggestion = None
    if current and mine > min(current):
        low = min(current)
        margin = f" Your margin would be Rs. {low - p['cost']:,.0f} per unit." if p["cost"] else ""
        suggestion = f"Matching the lowest in-stock price (Rs. {low:,.0f}) would cost Rs. {mine - low:,.0f} per unit.{margin}"
    return {"product": p, "your_price": mine, "own": own_pts, "series": series, "timeline": timeline[:40], "insight": insight, "suggestion": suggestion,
            "days": days, "market_avg": sum(current) / len(current) if current else None}


def competitor_health(day: str) -> list[dict]:
    out = []
    for c in db.query("SELECT * FROM competitors ORDER BY id"):
        tracked = db.one("SELECT COUNT(*) AS n FROM listings WHERE competitor_id=? AND status='confirmed'", (c["id"],))["n"]
        pending = db.one("SELECT COUNT(*) AS n FROM listings WHERE competitor_id=? AND status='pending'", (c["id"],))["n"]
        today = db.query("SELECT o.ok, o.error, o.checked_at FROM observations o JOIN listings l ON l.id=o.listing_id WHERE l.competitor_id=? AND o.day=? AND l.status='confirmed'",
                         (c["id"], day))
        week = db.query("SELECT o.ok FROM observations o JOIN listings l ON l.id=o.listing_id WHERE l.competitor_id=? AND o.day>? AND l.status='confirmed'",
                        (c["id"], (date.fromisoformat(day) - timedelta(days=7)).isoformat()))
        rate = round(100 * sum(o["ok"] for o in today) / len(today), 1) if today else None
        week_rate = round(100 * sum(o["ok"] for o in week) / len(week), 1) if week else None
        last = max((o["checked_at"] for o in today), default=None)
        errors = sorted({o["error"] for o in today if not o["ok"] and o["error"]})
        status = ("idle" if rate is None else "good" if rate >= 95 else "warn" if rate >= 60 else "bad") if c["active"] else "paused"
        out.append({**{k: c[k] for k in ("id", "name", "website", "color", "is_demo", "active", "price_selector", "stock_selector", "catalog_url")},
                    "tracked": tracked, "pending": pending, "success_rate": rate, "week_rate": week_rate, "last_check": last, "status": status, "errors": errors[:3]})
    return out
