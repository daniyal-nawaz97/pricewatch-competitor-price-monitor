"""Turn each day's observations into alerts, using the client's rules."""
from __future__ import annotations

from . import db

TYPES = {
    "price_drop": "Price drop", "price_increase": "Price increase", "cheaper_than_you": "Competitor cheaper than you",
    "out_of_stock": "Competitor out of stock", "back_in_stock": "Back in stock", "new_product": "New product found",
}


def add(day, type_, message, product_id=None, competitor_id=None, listing_id=None, old=None, new=None, severity="info"):
    return db.execute("INSERT INTO alerts(day, created_at, type, product_id, competitor_id, listing_id, old_price, new_price, message, severity) "
                      "VALUES(?,?,?,?,?,?,?,?,?,?)", (day, db.now(), type_, product_id, competitor_id, listing_id, old, new, message, severity))


def _fmt(v):
    return f"Rs. {v:,.0f}"


def evaluate(day: str, deliver: bool = True) -> int:
    """Create alerts for `day`. Returns the number of competitor price changes seen."""
    from .analytics import own_price_map
    settings = db.get_settings()
    rules = settings["rules"]
    db.execute("DELETE FROM alerts WHERE day=? AND type!='new_product'", (day,))  # re-running a day replaces its alerts
    prev_day = db.one("SELECT MAX(day) AS d FROM observations WHERE day<? AND ok=1", (day,))["d"]
    if not prev_day:
        return 0
    own_today, own_prev = own_price_map(day), own_price_map(prev_day)
    rows = db.query("""SELECT o.listing_id, o.price, o.in_stock, p.price AS prev_price, p.in_stock AS prev_stock, l.product_id, l.competitor_id,
                              pr.name AS product, pr.top, c.name AS competitor
                       FROM observations o JOIN observations p ON p.listing_id=o.listing_id AND p.day=?
                       JOIN listings l ON l.id=o.listing_id JOIN products pr ON pr.id=l.product_id JOIN competitors c ON c.id=l.competitor_id
                       WHERE o.day=? AND o.ok=1 AND p.ok=1 AND l.status='confirmed'""", (prev_day, day))
    changes = 0
    new_ids = []
    for r in rows:
        mine, mine_prev = own_today.get(r["product_id"]), own_prev.get(r["product_id"])
        if r["price"] != r["prev_price"]:
            changes += 1
            pct = (r["price"] - r["prev_price"]) / r["prev_price"] * 100
            if pct <= -rules["price_drop_pct"]:
                new_ids.append(add(day, "price_drop", f"{r['competitor']} dropped {r['product']} by {abs(pct):.0f}% ({_fmt(r['prev_price'])} → {_fmt(r['price'])}).",
                                   r["product_id"], r["competitor_id"], r["listing_id"], r["prev_price"], r["price"], "warn"))
            elif pct >= rules["price_increase_pct"]:
                new_ids.append(add(day, "price_increase", f"{r['competitor']} raised {r['product']} by {pct:.0f}% ({_fmt(r['prev_price'])} → {_fmt(r['price'])}).",
                                   r["product_id"], r["competitor_id"], r["listing_id"], r["prev_price"], r["price"], "good"))
        if mine and r["in_stock"]:
            under = (mine - r["price"]) / mine * 100
            under_prev = (mine_prev - r["prev_price"]) / mine_prev * 100 if mine_prev and r["prev_stock"] else -999
            if under >= rules["cheaper_than_you_pct"] and under_prev < rules["cheaper_than_you_pct"]:
                new_ids.append(add(day, "cheaper_than_you", f"{r['competitor']} is now {under:.0f}% cheaper than you on {r['product']} ({_fmt(r['price'])} vs your {_fmt(mine)}).",
                                   r["product_id"], r["competitor_id"], r["listing_id"], mine, r["price"], "high"))
        if r["prev_stock"] and not r["in_stock"] and (r["top"] or not rules.get("top_out_of_stock", True)):
            new_ids.append(add(day, "out_of_stock", f"{r['competitor']} is out of stock on {r['product']}{' (a top product)' if r['top'] else ''}. A chance to sell more.",
                               r["product_id"], r["competitor_id"], r["listing_id"], severity="good"))
        if rules.get("back_in_stock", True) and not r["prev_stock"] and r["in_stock"] and (r["top"] or not rules.get("top_out_of_stock", True)):
            new_ids.append(add(day, "back_in_stock", f"{r['competitor']} has {r['product']} back in stock at {_fmt(r['price'])}.",
                               r["product_id"], r["competitor_id"], r["listing_id"], new=r["price"], severity="info"))
    if deliver:
        from . import notify
        notify.alerts_digest(day)
    return changes
