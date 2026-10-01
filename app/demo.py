"""Demo store and three FICTITIOUS competitor shops.

The shops are real web pages served by this app (see /demo-shops/...), and the collector reads them over HTTP exactly
like it reads real competitor sites. Their prices come from a deterministic simulation anchored to the day the demo
was created, so history stays consistent. All names, brands and prices are invented.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from datetime import date, timedelta
from functools import lru_cache
from html import escape

BRANDS = ["Voltix", "Zenpower", "Nexo", "Orbit", "Pulse"]

# (category, name template, base price PKR)
CATALOG = [
    ("Chargers", "Voltix 20W USB-C Fast Charger", 1499), ("Chargers", "Voltix 25W PD Wall Charger", 1899),
    ("Chargers", "Zenpower 33W Dual Port Charger", 2499), ("Chargers", "Zenpower 65W GaN Charger", 5499),
    ("Chargers", "Nexo 15W Wireless Charging Pad", 2299), ("Chargers", "Nexo 3-in-1 Wireless Charging Stand", 6999),
    ("Chargers", "Orbit 45W Super Fast Charger", 3299), ("Chargers", "Pulse 12W Travel Charger", 899),
    ("Cables", "Voltix USB-C to USB-C Cable 1m 60W", 699), ("Cables", "Voltix USB-C to USB-C Cable 2m 100W", 1199),
    ("Cables", "Zenpower USB-C to Lightning Cable 1m", 1299), ("Cables", "Zenpower Micro USB Cable 1m", 399),
    ("Cables", "Nexo Braided USB-C Cable 2m", 899), ("Cables", "Nexo 3-in-1 Charging Cable 1.2m", 999),
    ("Cables", "Orbit Magnetic USB-C Cable 1m", 1099), ("Cables", "Pulse USB-A to USB-C Cable 1m", 349),
    ("Earbuds", "Pulse Buds Lite True Wireless Earbuds", 3499), ("Earbuds", "Pulse Buds Pro ANC Earbuds", 8999),
    ("Earbuds", "Orbit Neckband Sport Earphones", 2199), ("Earbuds", "Orbit Over-Ear Wireless Headphones", 7499),
    ("Earbuds", "Nexo Gaming Earbuds Low Latency", 4299), ("Earbuds", "Zenpower Open-Ear Sport Earbuds", 5999),
    ("Earbuds", "Voltix Wired Earphones with Mic", 599), ("Earbuds", "Pulse Kids Headphones", 2499),
    ("Power Banks", "Voltix 10000mAh 20W Power Bank", 3999), ("Power Banks", "Voltix 20000mAh 22.5W Power Bank", 5999),
    ("Power Banks", "Zenpower 30000mAh Power Bank", 7999), ("Power Banks", "Nexo 5000mAh Magnetic Power Bank", 4499),
    ("Power Banks", "Orbit 10000mAh Slim Power Bank", 3499), ("Power Banks", "Pulse 20000mAh Laptop Power Bank 65W", 11999),
    ("Cases", "Orbit Clear Shockproof Case for iPhone 15", 999), ("Cases", "Orbit Clear Shockproof Case for Galaxy S24", 999),
    ("Cases", "Nexo Silicone Case for iPhone 15 Pro", 1299), ("Cases", "Nexo Leather Flip Case for Galaxy A55", 1499),
    ("Cases", "Zenpower Rugged Armor Case for Pixel 8", 1799), ("Cases", "Pulse Magnetic Case for iPhone 14", 1599),
    ("Screen Protectors", "Voltix Tempered Glass for iPhone 15 (2 Pack)", 799), ("Screen Protectors", "Voltix Privacy Glass for iPhone 15 Pro", 1199),
    ("Screen Protectors", "Orbit Tempered Glass for Galaxy S24", 699), ("Screen Protectors", "Orbit Camera Lens Protector for iPhone 15", 599),
    ("Screen Protectors", "Nexo Matte Glass for Galaxy A55", 649), ("Screen Protectors", "Zenpower Hydrogel Film for Pixel 8", 499),
    ("Smart Watches", "Pulse Fit 2 Smart Watch", 6499), ("Smart Watches", "Pulse Fit 2 Pro AMOLED Smart Watch", 9999),
    ("Smart Watches", "Orbit Kids GPS Watch", 7999), ("Smart Watches", "Nexo Fitness Band 5", 3999),
    ("Smart Watches", "Zenpower Silicone Watch Strap 22mm", 499), ("Smart Watches", "Voltix Magnetic Watch Charger", 899),
    ("Car Accessories", "Voltix 38W Dual Car Charger", 1799), ("Car Accessories", "Orbit Magnetic Car Phone Mount", 1499),
    ("Car Accessories", "Nexo Wireless Car Charger Mount 15W", 4499), ("Car Accessories", "Zenpower Bluetooth FM Transmitter", 2799),
    ("Car Accessories", "Pulse Dash Cam 1080p", 8999), ("Car Accessories", "Orbit Car Seat Gap Organizer", 999),
    ("Chargers", "Pulse 100W 4-Port GaN Desktop Charger", 9499), ("Earbuds", "Voltix Bluetooth Speaker Mini", 3299),
]
NEW_PRODUCT = ("Chargers", "Zenpower 30W MagSafe Compatible Charger", 3999)  # appears at TechBazaar on the demo day

COMPETITORS = [
    {"slug": "chargezone", "name": "ChargeZone", "color": "#0ea5e9", "factor": 0.985, "coverage": 0.9, "style": "jsonld"},
    {"slug": "techbazaar", "name": "TechBazaar", "color": "#f97316", "factor": 1.04, "coverage": 0.85, "style": "microdata"},
    {"slug": "mobimart", "name": "MobiMart", "color": "#10b981", "factor": 1.08, "coverage": 0.8, "style": "plain",
     "price_selector": ".pd-price .now", "stock_selector": ".stock"},
]
EPOCH_OFFSET = 150  # simulation starts this many days before the anchor


def _h(*parts) -> int:
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


def sku_of(i: int) -> str:
    return f"GH-{1001 + i}"


def handle(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def own_catalog():
    out = []
    for i, (cat, name, price) in enumerate(CATALOG):
        brand = name.split()[0]
        out.append({"sku": sku_of(i), "name": name, "brand": brand, "category": cat, "price": float(price),
                    "cost": round(price * (0.62 + (_h("cost", i) % 12) / 100)), "top": 1 if _h("top", i) % 100 < 36 else 0})
    return out


def competitor_title(comp_slug: str, name: str) -> str:
    """Competitors name the same product differently, so matching isn't trivial."""
    words = name.split()
    brand, rest = words[0], " ".join(words[1:])
    if comp_slug == "chargezone":
        colour = ["Black", "White", "Blue"][_h(comp_slug, name) % 3]
        return f"{brand} {rest} - {colour}"
    if comp_slug == "techbazaar":
        rest = rest.replace("USB-C", "Type-C").replace("Power Bank", "Powerbank").replace("Earbuds", "TWS Earbuds")
        return f"{brand} {rest} (Original)"
    if _h("wording", name) % 7 == 0:  # some listings use different words: these need a person to confirm the match
        for a, b in (("Charger", "Adapter"), ("Earbuds", "Airdots"), ("Case", "Back Cover"), ("Cable", "Data Line"),
                     ("Power Bank", "Portable Battery"), ("Smart Watch", "Smartwatch"), ("Mount", "Holder")):
            rest = rest.replace(a, b)
    return f"{brand.upper()} {rest} | 1 Year Warranty"


@lru_cache(maxsize=None)
def _series(comp_slug: str, sku: str, base: float, anchor_iso: str):
    """Daily (price, regular_price, in_stock) from EPOCH to anchor+400 days."""
    comp = next(c for c in COMPETITORS if c["slug"] == comp_slug)
    anchor = date.fromisoformat(anchor_iso)
    start = anchor - timedelta(days=EPOCH_OFFSET)
    rng = random.Random(_h("series", comp_slug, sku))
    level = base * comp["factor"] * (1 + rng.uniform(-0.06, 0.06))
    out, oos_left = {}, 0
    idx = int(sku.split("-")[1]) - 1001 if sku.split("-")[1].isdigit() else 999
    for n in range(EPOCH_OFFSET + 400):
        d = start + timedelta(days=n)
        rel = (d - anchor).days
        if rng.random() < 0.075:  # occasional repricing, pulled back toward the shop's usual level
            target = base * comp["factor"]
            level = level + (target - level) * 0.35
            level *= 1 + rng.choice([-1, 1]) * rng.uniform(0.02, 0.07)
            level = min(max(level, base * 0.82), base * 1.22)
        price = level
        regular = None
        # TechBazaar price war: undercuts 12 products by ~11% from anchor-12 to anchor-6
        if comp_slug == "techbazaar" and -12 <= rel <= -6 and idx % 4 == 0 and idx < 48:
            regular, price = level, level * 0.89
        # MobiMart weekend sale: 10% off everything, anchor-20 .. anchor-18
        if comp_slug == "mobimart" and -20 <= rel <= -18:
            regular, price = level, level * 0.90
        # stock-outs
        if oos_left > 0:
            oos_left -= 1
            in_stock = False
        else:
            in_stock = True
            if rng.random() < (0.035 if comp_slug == "mobimart" else 0.012):
                oos_left = rng.randint(1, 4)
        # scripted events on the demo day so the alerts feed has something to show
        if rel == 0:
            if comp_slug == "chargezone" and sku == "GH-1001":
                price = level = level * 0.93  # the 7% drop the morning report leads with
            if comp_slug == "techbazaar" and sku in ("GH-1025", "GH-1018"):
                in_stock = False
            if comp_slug == "mobimart" and sku == "GH-1044":
                in_stock = True
        p = round(price / 10) * 10 - 1 if price > 100 else round(price)  # retail-style prices: 1,399 / 2,249
        out[d.isoformat()] = (float(p), float(round(regular / 10) * 10 - 1) if regular else None, in_stock)
    return out


def carries(comp_slug: str, sku: str) -> bool:
    comp = next(c for c in COMPETITORS if c["slug"] == comp_slug)
    return _h("carry", comp_slug, sku) % 100 < comp["coverage"] * 100 or sku in ("GH-1001", "GH-1025", "GH-1018", "GH-1044")


def offer(comp_slug: str, sku: str, day: date, anchor: date):
    """What this competitor shows for this product on this day, or None if they don't sell it."""
    items = {p["sku"]: p for p in own_catalog()}
    if sku == "GH-NEW":
        if comp_slug != "techbazaar" or day < anchor:
            return None
        base = NEW_PRODUCT[2]
    else:
        if sku not in items or not carries(comp_slug, sku):
            return None
        base = items[sku]["price"]
    return _series(comp_slug, sku, base, anchor.isoformat()).get(day.isoformat())


def own_price(sku: str, base: float, day: date, anchor: date) -> float:
    """Our store's own price history: a few repricings, incl. reacting to the price war."""
    rel = (day - anchor).days
    idx = int(sku.split("-")[1]) - 1001
    p = base
    if idx % 9 == 0 and rel >= -30:
        p = base * 1.05
    if idx % 4 == 0 and idx < 48 and idx % 8 == 0 and rel >= -5:
        p = base * 0.95  # matched part of TechBazaar's price war
    return float(round(p / 10) * 10 - 1) if p != base else base


# --------------------------------------------------------------------------- shop pages
def _page(comp, title, body):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} | {comp['name']}</title>
<style>body{{font-family:Arial,sans-serif;margin:0;color:#222}}header{{background:{comp['color']};color:#fff;padding:14px 28px;font-size:22px;font-weight:700}}
.demo{{background:#fff7ed;color:#9a3412;font-size:13px;padding:6px 28px}}main{{padding:24px 28px;max-width:900px}}a{{color:{comp['color']}}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}}.card{{border:1px solid #eee;border-radius:8px;padding:12px}}</style></head>
<body><div class="demo">Fictitious demo shop used by PriceWatch. Not a real store; products and prices are invented.</div>
<header>{comp['name']}</header><main>{body}</main></body></html>"""


def shop_catalog_html(comp_slug: str, today: date, anchor: date) -> str:
    comp = next(c for c in COMPETITORS if c["slug"] == comp_slug)
    cards = []
    for p in own_catalog() + [{"sku": "GH-NEW", "name": NEW_PRODUCT[1]}]:
        o = offer(comp_slug, p["sku"], today, anchor)
        if not o:
            continue
        title = competitor_title(comp_slug, p["name"])
        cards.append(f'<div class="card"><a class="product-link" href="/demo-shops/{comp_slug}/p/{handle(title)}">{escape(title)}</a>'
                     f'<div>Rs. {o[0]:,.0f}</div></div>')
    return _page(comp, "All products", f"<h1>All products</h1><div class='grid'>{''.join(cards)}</div>")


def find_by_handle(comp_slug: str, h: str):
    for p in own_catalog() + [{"sku": "GH-NEW", "name": NEW_PRODUCT[1]}]:
        if handle(competitor_title(comp_slug, p["name"])) == h:
            return p
    return None


def shop_product_html(comp_slug: str, h: str, today: date, anchor: date) -> str | None:
    comp = next(c for c in COMPETITORS if c["slug"] == comp_slug)
    p = find_by_handle(comp_slug, h)
    if not p:
        return None
    o = offer(comp_slug, p["sku"], today, anchor)
    if not o:
        return None
    price, regular, in_stock = o
    title = competitor_title(comp_slug, p["name"])
    if comp["style"] == "jsonld":
        ld = {"@context": "https://schema.org", "@type": "Product", "name": title, "sku": f"CZ-{p['sku'][3:]}",
              "offers": {"@type": "Offer", "price": f"{price:.0f}", "priceCurrency": "PKR",
                         "availability": "https://schema.org/" + ("InStock" if in_stock else "OutOfStock")}}
        body = (f'<script type="application/ld+json">{json.dumps(ld)}</script><h1>{escape(title)}</h1>'
                f'<p style="font-size:26px;font-weight:700">Rs. {price:,.0f}</p>'
                + (f'<p><s>Rs. {regular:,.0f}</s> Sale!</p>' if regular else "")
                + f'<p>{"In stock, ships in 24 hours" if in_stock else "Sold out"}</p><button>Add to cart</button>')
    elif comp["style"] == "microdata":
        body = (f'<div itemscope itemtype="https://schema.org/Product"><h1 itemprop="name">{escape(title)}</h1>'
                f'<div itemprop="offers" itemscope itemtype="https://schema.org/Offer"><meta itemprop="priceCurrency" content="PKR">'
                f'<span itemprop="price" content="{price:.0f}" style="font-size:26px;font-weight:700">Rs. {price:,.0f}</span> '
                + (f'<del class="was">Rs. {regular:,.0f}</del>' if regular else "")
                + f'<link itemprop="availability" href="https://schema.org/{"InStock" if in_stock else "OutOfStock"}"></div>'
                f'<p>Cash on delivery available.</p></div>')
    else:
        body = (f'<h1 class="pd-title">{escape(title)}</h1><div class="pd-price"><span class="now">Rs {price:,.0f}</span> '
                + (f'<span class="old">Rs {regular:,.0f}</span>' if regular else "") + '</div>'
                f'<div class="stock">{"Available" if in_stock else "Out of stock"}</div><p>Free delivery over Rs 3,000.</p>')
    return _page(comp, title, body)
