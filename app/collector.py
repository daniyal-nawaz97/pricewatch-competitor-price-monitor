"""Daily collector: visits competitor product pages gently, reads price / regular price / stock, and stores every observation.

Reading order for each page (works on most online stores without any setup):
  1. schema.org JSON-LD  (<script type="application/ld+json"> Product/Offer)
  2. schema.org microdata (itemprop="price", itemprop="availability")
  3. Open Graph / product meta tags (product:price:amount, og:availability)
  4. the competitor's custom CSS selectors (set in Competitors for sites without structured data)
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import date, datetime, timedelta, timezone
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from . import db, matching
from .config import REQUEST_DELAY_SECONDS, REQUEST_TIMEOUT, SELF_URL, USER_AGENT

log = logging.getLogger("pricewatch.collector")
_run_lock = threading.Lock()
OUT_OF_STOCK = re.compile(r"out\s*of\s*stock|sold\s*out|unavailable|not\s*available|coming\s*soon", re.I)


class ParseError(Exception):
    pass


def to_price(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"(?i)pkr|rs\.?|usd|aed|[$£€]", "", str(v)).strip()
    m = re.search(r"\d[\d,]*(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def _avail(v) -> bool | None:
    if v is None:
        return None
    s = str(v).lower()
    if any(k in s for k in ("outofstock", "out of stock", "soldout", "discontinued", "outofstock")):
        return False
    if any(k in s for k in ("instock", "in stock", "limitedavailability", "preorder", "available")):
        return True
    return None


def _jsonld(soup):
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node); continue
            if not isinstance(node, dict):
                continue
            if "@graph" in node:
                stack.extend(node["@graph"])
            types = node.get("@type")
            types = types if isinstance(types, list) else [types]
            if "Product" in types:
                offers = node.get("offers") or {}
                offers = offers[0] if isinstance(offers, list) and offers else offers
                if isinstance(offers, dict):
                    price = to_price(offers.get("price") or offers.get("lowPrice"))
                    if price is not None:
                        return {"price": price, "in_stock": _avail(offers.get("availability")), "title": node.get("name")}
    return None


def _microdata(soup):
    el = soup.find(attrs={"itemprop": "price"})
    if not el:
        return None
    price = to_price(el.get("content") or el.get_text())
    if price is None:
        return None
    av = soup.find(attrs={"itemprop": "availability"})
    name = soup.find(attrs={"itemprop": "name"})
    return {"price": price, "in_stock": _avail(av.get("href") or av.get("content") or av.get_text()) if av else None,
            "title": name.get_text(strip=True) if name else None}


def _meta(soup):
    for key in ("product:price:amount", "og:price:amount", "twitter:data1"):
        el = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if el and to_price(el.get("content")) is not None:
            av = soup.find("meta", attrs={"property": "og:availability"}) or soup.find("meta", attrs={"property": "product:availability"})
            return {"price": to_price(el.get("content")), "in_stock": _avail(av.get("content")) if av else None, "title": None}
    return None


def parse_page(html: str, competitor: dict) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    result = None
    if competitor.get("price_selector"):
        el = soup.select_one(competitor["price_selector"])
        if el and to_price(el.get_text()) is not None:
            result = {"price": to_price(el.get_text()), "in_stock": None, "title": None, "method": "selector"}
    for method, fn in (("json-ld", _jsonld), ("microdata", _microdata), ("meta", _meta)):
        if result:
            break
        r = fn(soup)
        if r:
            result = {**r, "method": method}
    if not result:
        raise ParseError("No price found on the page. Add a price selector for this competitor.")
    if competitor.get("stock_selector"):
        el = soup.select_one(competitor["stock_selector"])
        if el:
            result["in_stock"] = not OUT_OF_STOCK.search(el.get_text())
    if result["in_stock"] is None:
        body = soup.get_text(" ", strip=True)[:6000]
        result["in_stock"] = not OUT_OF_STOCK.search(body)
    # a crossed-out "regular" price means a discount
    regular = None
    for sel in ("del", "s", ".was", ".old", ".compare-at", ".price--compare", ".regular-price"):
        el = soup.select_one(sel)
        if el:
            v = to_price(el.get_text())
            if v and v > result["price"]:
                regular = v
                break
    result["regular_price"] = regular
    if not result.get("title"):
        h1 = soup.find("h1")
        result["title"] = h1.get_text(strip=True) if h1 else (soup.title.get_text(strip=True) if soup.title else None)
    return result


# --------------------------------------------------------------------------- fetching (polite)
_robots: dict[str, robotparser.RobotFileParser | None] = {}


def allowed(url: str) -> bool:
    host = urlparse(url)
    if url.startswith(SELF_URL):
        return True
    key = f"{host.scheme}://{host.netloc}"
    if key not in _robots:
        rp = robotparser.RobotFileParser()
        try:
            r = httpx.get(key + "/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=10, follow_redirects=True)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            _robots[key] = rp
        except httpx.HTTPError:
            _robots[key] = None
    rp = _robots[key]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)


def fetch(url: str, client: httpx.Client) -> str:
    if not allowed(url):
        raise ParseError("The site's robots.txt asks bots not to read this page.")
    r = client.get(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en"}, timeout=REQUEST_TIMEOUT, follow_redirects=True)
    if r.status_code == 404:
        raise ParseError("Page not found (the product may have been removed).")
    if r.status_code in (403, 429):
        raise ParseError(f"The site refused the request ({r.status_code}). It may be blocking bots.")
    r.raise_for_status()
    return r.text


def resolve(url: str) -> str:
    """Demo listings are stored with a relative /demo-shops/... path so they work on any host."""
    return SELF_URL + url if url.startswith("/") else url


def check_listing(listing: dict, competitor: dict, client: httpx.Client) -> dict:
    try:
        html = fetch(resolve(listing["url"]), client)
        r = parse_page(html, competitor)
        return {"ok": 1, "price": r["price"], "regular_price": r["regular_price"], "in_stock": int(bool(r["in_stock"])), "error": None,
                "method": r["method"], "title": r["title"]}
    except ParseError as e:
        return {"ok": 0, "error": str(e)}
    except httpx.HTTPError as e:
        return {"ok": 0, "error": f"Site not reachable ({type(e).__name__})."}


def record(listing_id: int, day: str, res: dict, source="live"):
    db.execute("INSERT INTO observations(listing_id, day, checked_at, ok, price, regular_price, in_stock, error, source) VALUES(?,?,?,?,?,?,?,?,?) "
               "ON CONFLICT(listing_id, day) DO UPDATE SET checked_at=excluded.checked_at, ok=excluded.ok, price=excluded.price, "
               "regular_price=excluded.regular_price, in_stock=excluded.in_stock, error=excluded.error, source=excluded.source",
               (listing_id, day, db.now(), res["ok"], res.get("price"), res.get("regular_price"), res.get("in_stock"), res.get("error"), source))


def discover(competitor: dict, client: httpx.Client, day: str) -> int:
    """Read the competitor's catalogue page and queue unknown products for Match review."""
    if not competitor.get("catalog_url"):
        return 0
    try:
        html = fetch(resolve(competitor["catalog_url"]), client)
    except (ParseError, httpx.HTTPError):
        return 0
    soup = BeautifulSoup(html, "html.parser")
    base = resolve(competitor["catalog_url"])
    links = soup.select("a.product-link") or [a for a in soup.find_all("a", href=True) if re.search(r"/(p|product|products)/", a["href"])]
    known = {r["url"] for r in db.query("SELECT url FROM listings WHERE competitor_id=?", (competitor["id"],))}
    products = db.query("SELECT id, name FROM products WHERE active=1")
    added = 0
    for a in links:
        href = a["href"]
        url = href if href.startswith("/demo-shops/") else urljoin(base, href)
        if url in known:
            continue
        title = a.get_text(strip=True)
        p, s = matching.best_match(title, products)
        db.execute("INSERT OR IGNORE INTO listings(product_id, competitor_id, url, title, status, confidence, created_at) VALUES(?,?,?,?,?,?,?)",
                   (p["id"] if p and s >= 0.55 else None, competitor["id"], url, title, "pending", s, db.now()))
        if not p or s < 0.55:
            from . import alerts
            alerts.add(day, "new_product", f"{competitor['name']} started selling “{title}”, which isn't in your catalogue.",
                       competitor_id=competitor["id"], severity="info")
        added += 1
        known.add(url)
    return added


def run(trigger: str = "manual", day: str | None = None, deliver: bool = True) -> dict:
    """Check every confirmed listing once. Returns the run summary."""
    if not _run_lock.acquire(blocking=False):
        return {"status": "busy"}
    try:
        day = day or date.today().isoformat()
        run_id = db.execute("INSERT INTO runs(day, started_at, trigger, status) VALUES(?,?,?,?)", (day, db.now(), trigger, "running"))
        comps = {c["id"]: c for c in db.query("SELECT * FROM competitors WHERE active=1")}
        listings = db.query("SELECT * FROM listings WHERE status='confirmed' ORDER BY competitor_id, id")
        ok = failed = 0
        with httpx.Client() as client:
            for comp in comps.values():
                discover(comp, client, day)
            last_host, t_last = None, 0.0
            for l in listings:
                comp = comps.get(l["competitor_id"])
                if not comp:
                    continue
                host = urlparse(resolve(l["url"])).netloc
                delay = 0.02 if comp["is_demo"] else REQUEST_DELAY_SECONDS
                if host == last_host and time.time() - t_last < delay:
                    time.sleep(delay - (time.time() - t_last))
                res = check_listing(l, comp, client)
                last_host, t_last = host, time.time()
                record(l["id"], day, res)
                ok += res["ok"]; failed += 1 - res["ok"]
        from . import alerts, reports
        changes = alerts.evaluate(day, deliver=deliver)
        db.execute("UPDATE runs SET finished_at=?, pages=?, ok=?, failed=?, changes=?, status='done' WHERE id=?",
                   (db.now(), ok + failed, ok, failed, changes, run_id))
        reports.build_daily(day)
        if date.fromisoformat(day).strftime("%A") == db.get_settings().get("weekly_day", "Monday"):
            reports.build_weekly(day)
        return {"status": "done", "pages": ok + failed, "ok": ok, "failed": failed, "changes": changes}
    finally:
        _run_lock.release()


def last_run():
    return db.one("SELECT * FROM runs ORDER BY id DESC LIMIT 1")


def run_async(trigger="manual"):
    threading.Thread(target=run, kwargs={"trigger": trigger}, daemon=True).start()
