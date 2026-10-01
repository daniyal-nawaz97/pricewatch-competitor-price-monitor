"""Measure collection accuracy and the numbers for the case study.

Run while the app has data (it reads the same DATA_DIR):
    python -m scripts.evaluate

1. Accuracy: every price collected LIVE today is compared with the price the demo shop page actually shows
   (the shops' ground truth). For real competitors, spot-check 20 products by hand instead.
2. Reliability: share of pages read successfully, today and over the last 7 days.
3. Activity: price changes detected per week, alerts, and an example insight.
Writes docs/results.md and docs/results.json.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from app import analytics, db, demo  # noqa: E402
from app.config import MANUAL_SECONDS_PER_CHECK  # noqa: E402


def main():
    s = db.get_settings()
    anchor = date.fromisoformat(s["demo_anchor"]) if s.get("demo_anchor") else date.today()
    day = db.one("SELECT MAX(day) AS d FROM observations WHERE source='live'")["d"]
    if not day:
        print("No live collection yet. Start the app first so it checks today's prices.")
        return
    live = db.query("""SELECT o.*, l.url, p.sku, c.name AS competitor, c.is_demo FROM observations o JOIN listings l ON l.id=o.listing_id
                       JOIN products p ON p.id=l.product_id JOIN competitors c ON c.id=l.competitor_id WHERE o.day=? AND o.source='live'""", (day,))
    slug = {c["name"]: c["slug"] for c in demo.COMPETITORS}
    checked = correct = stock_ok = 0
    wrong = []
    for o in live:
        if not o["is_demo"] or not o["ok"]:
            continue
        truth = demo.offer(slug[o["competitor"]], o["sku"], date.fromisoformat(day), anchor)
        if not truth:
            continue
        checked += 1
        if abs(truth[0] - o["price"]) < 0.01:
            correct += 1
        else:
            wrong.append(f"{o['competitor']} {o['sku']}: read {o['price']}, page shows {truth[0]}")
        stock_ok += int(bool(truth[2]) == bool(o["in_stock"]))
    ok_today = sum(o["ok"] for o in live)
    week_start = (date.fromisoformat(day) - timedelta(days=6)).isoformat()
    week = db.query("SELECT ok FROM observations WHERE day BETWEEN ? AND ?", (week_start, day))
    changes_week = sum(len(analytics.changes_on((date.fromisoformat(day) - timedelta(days=i)).isoformat())) for i in range(7))
    alerts_week = Counter(r["type"] for r in db.query("SELECT type FROM alerts WHERE day BETWEEN ? AND ?", (week_start, day)))
    # example insight: the competitor that undercut you on the most products in any 7-day window of the history
    best = None
    for i in range(0, 60, 1):
        end = date.fromisoformat(day) - timedelta(days=i)
        rows = db.query("""SELECT c.name, COUNT(DISTINCT a.product_id) AS n FROM alerts a JOIN competitors c ON c.id=a.competitor_id
                           WHERE a.type IN ('cheaper_than_you','price_drop') AND a.day BETWEEN ? AND ? GROUP BY c.name ORDER BY n DESC LIMIT 1""",
                        ((end - timedelta(days=6)).isoformat(), end.isoformat()))
        if rows and (not best or rows[0]["n"] > best[1]):
            best = (rows[0]["name"], rows[0]["n"], (end - timedelta(days=6)).isoformat(), end.isoformat())
    listings = db.one("SELECT COUNT(*) AS n FROM listings WHERE status='confirmed'")["n"]
    products = db.one("SELECT COUNT(*) AS n FROM products WHERE active=1")["n"]
    comps = db.one("SELECT COUNT(*) AS n FROM competitors WHERE active=1")["n"]
    run = db.one("SELECT * FROM runs WHERE day=? AND trigger!='demo-backfill' ORDER BY id DESC LIMIT 1", (day,))
    summary = {
        "date": day, "products": products, "competitors": comps, "pages": listings,
        "live_prices_checked": checked, "live_prices_correct": correct, "price_accuracy": round(100 * correct / checked, 1) if checked else None,
        "stock_accuracy": round(100 * stock_ok / checked, 1) if checked else None,
        "success_rate_today": round(100 * ok_today / len(live), 1) if live else None,
        "success_rate_week": round(100 * sum(w["ok"] for w in week) / len(week), 1) if week else None,
        "changes_per_week": changes_week, "alerts_week": dict(alerts_week),
        "example_insight": f"{best[0]} undercut or cut prices on {best[1]} of your products in one week ({best[2]} to {best[3]})." if best else None,
        "hours_saved_per_week": round(listings * 7 * MANUAL_SECONDS_PER_CHECK / 3600, 1),
        "run_seconds": None,
    }
    if run and run["finished_at"]:
        from datetime import datetime
        summary["run_seconds"] = round((datetime.fromisoformat(run["finished_at"]) - datetime.fromisoformat(run["started_at"])).total_seconds(), 1)
    (BASE / "docs" / "results.json").write_text(json.dumps(summary, indent=2))
    (BASE / "static" / "results.json").write_text(json.dumps(summary, indent=2))
    md = [f"# Measured results ({day})", "",
          f"Demo store: {products} products, {comps} fictitious competitor websites, {listings} product pages tracked.", "",
          "| Metric | Result |", "|---|---|",
          f"| Prices read live today that match the page exactly | **{correct} of {checked} ({summary['price_accuracy']}%)** |",
          f"| Stock status read correctly | {summary['stock_accuracy']}% |",
          f"| Pages read successfully today | {summary['success_rate_today']}% |",
          f"| Pages read successfully, last 7 days | {summary['success_rate_week']}% |",
          f"| Time for a full check of all pages | {summary['run_seconds']} s (demo shops, no delay; real sites are read 1.5 s apart per site) |",
          f"| Competitor price changes detected, last 7 days | {changes_week} |",
          f"| Alerts raised, last 7 days | {sum(alerts_week.values())} ({', '.join(f'{v} {k.replace(chr(95), chr(32))}' for k, v in alerts_week.most_common())}) |",
          f"| Example insight | {summary['example_insight']} |",
          f"| Manual checking avoided | about {summary['hours_saved_per_week']} hours per week (at {MANUAL_SECONDS_PER_CHECK:g} s per page, daily) |", "",
          "**Honest notes**", "",
          "- Today's prices were collected live over HTTP from the three demo shop websites by the real collector (JSON-LD, microdata and a custom CSS selector). "
          "History before today was simulated with the same price model, so weekly figures describe the demo market, not a real one.",
          "- The collector was also tested on books.toscrape.com (a public site made for scraping practice): price, stock and title were read correctly with a custom selector.",
          "- With real competitors, websites can change or block bots. The Competitors page shows success rates per site so problems are spotted the same day."]
    if wrong:
        md += ["", "Mismatches:", *[f"- {w}" for w in wrong[:20]]]
    (BASE / "docs" / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[4:15]))


if __name__ == "__main__":
    main()
