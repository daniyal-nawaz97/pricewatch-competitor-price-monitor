"""Daily morning report and weekly summary: HTML email, PDF and Excel."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from html import escape

from . import analytics, db
from .config import PUBLIC_BASE_URL, REPORTS_DIR


def _fmt(v):
    return "—" if v is None else f"{v:,.0f}"


def _nice(day: str) -> str:
    return date.fromisoformat(day).strftime("%-d %B")


# --------------------------------------------------------------------------- data
def daily_data(day: str) -> dict:
    snap = analytics.snapshot(day)
    tracked = [r for r in snap if r["position"] != "untracked"]
    changes = analytics.changes_on(day)
    alerts = db.query("SELECT * FROM alerts WHERE day=? ORDER BY CASE severity WHEN 'high' THEN 0 WHEN 'warn' THEN 1 WHEN 'good' THEN 2 ELSE 3 END, id", (day,))
    attention = sum(1 for a in alerts if a["severity"] in ("high", "warn"))
    return {
        "day": day, "changes": len(changes), "attention": attention,
        "cheaper": sum(1 for r in tracked if r["position"] == "cheapest"),
        "pricier": sum(1 for r in tracked if r["cheapest"] is not None and r["price"] > r["cheapest"]),
        "tracked": len(tracked),
        "moves": [{"product": c["product"], "competitor": c["competitor"], "from": c["prev_price"], "to": c["price"], "pct": round(c["pct"], 1)} for c in changes[:10]],
        "alerts": [{"type": a["type"], "message": a["message"], "severity": a["severity"]} for a in alerts[:15]],
        "positions": [{"sku": r["sku"], "name": r["name"], "category": r["category"], "price": r["price"], "cheapest": r["cheapest"],
                       "gap_pct": None if r["gap_pct"] is None else round(r["gap_pct"], 1), "position": r["position"],
                       "competitors": {str(k): v.get("price") for k, v in r["competitors"].items()}} for r in snap],
    }


def weekly_data(day: str) -> dict:
    end = date.fromisoformat(day)
    start = (end - timedelta(days=6)).isoformat()
    week_ago = (end - timedelta(days=7)).isoformat()
    first = {}
    last = {}
    for o in db.query("""SELECT o.listing_id, o.day, o.price, l.product_id, l.competitor_id, p.name AS product, c.name AS competitor
                         FROM observations o JOIN listings l ON l.id=o.listing_id JOIN products p ON p.id=l.product_id JOIN competitors c ON c.id=l.competitor_id
                         WHERE o.ok=1 AND l.status='confirmed' AND o.day BETWEEN ? AND ? ORDER BY o.day""", (week_ago, day)):
        first.setdefault(o["listing_id"], o)
        last[o["listing_id"]] = o
    movers = []
    for lid, a in first.items():
        b = last[lid]
        if a["price"] and b["price"] != a["price"]:
            movers.append({"product": b["product"], "competitor": b["competitor"], "from": a["price"], "to": b["price"], "pct": round((b["price"] - a["price"]) / a["price"] * 100, 1)})
    movers.sort(key=lambda m: -abs(m["pct"]))
    alerts = db.query("SELECT a.*, c.name AS competitor FROM alerts a LEFT JOIN competitors c ON c.id=a.competitor_id WHERE a.day BETWEEN ? AND ?", (start, day))
    aggression = Counter(a["competitor"] for a in alerts if a["type"] in ("price_drop", "cheaper_than_you") and a["competitor"])
    undercut = defaultdict(set)
    for a in alerts:
        if a["type"] == "cheaper_than_you" and a["competitor"]:
            undercut[a["competitor"]].add(a["product_id"])
    before = {r["id"]: r for r in analytics.snapshot(week_ago)}
    now = analytics.snapshot(day)
    lost, gained = [], []
    for r in now:
        b = before.get(r["id"])
        if not b or b["rank"] is None or r["rank"] is None:
            continue
        if r["rank"] > b["rank"]:
            lost.append({"product": r["name"], "from": b["rank"], "to": r["rank"], "of": r["of"]})
        elif r["rank"] < b["rank"]:
            gained.append({"product": r["name"], "from": b["rank"], "to": r["rank"], "of": r["of"]})
    most = aggression.most_common(1)[0] if aggression else None
    return {"day": day, "start": start, "movers": movers[:12], "price_changes": len(movers),
            "most_aggressive": {"competitor": most[0], "moves": most[1], "products_undercut": len(undercut[most[0]])} if most else None,
            "aggression": dict(aggression), "lost": lost[:12], "gained": gained[:12],
            "alerts": Counter(a["type"] for a in alerts)}


# --------------------------------------------------------------------------- email HTML (inline styles, phone friendly)
def _email(title: str, numbers: list[tuple[str, str, str]], blocks: str, company: str, accent: str) -> str:
    link = f"{PUBLIC_BASE_URL}/#/" if PUBLIC_BASE_URL else "#"
    nums = "".join(f'<td style="padding:6px;width:33%"><div style="background:#f6f7f9;border-radius:10px;padding:12px 8px;text-align:center">'
                   f'<div style="font-size:24px;font-weight:800;color:{c}">{escape(v)}</div><div style="font-size:12px;color:#6b7280">{escape(l)}</div></div></td>'
                   for v, l, c in numbers)
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(title)}</title></head><body style="margin:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;color:#111827">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:16px 8px">
<table role="presentation" width="100%" style="max-width:560px;background:#fff;border-radius:14px;overflow:hidden" cellpadding="0" cellspacing="0">
<tr><td style="background:{accent};color:#fff;padding:18px 20px"><div style="font-size:13px;opacity:.85">{escape(company)} · PriceWatch</div>
<div style="font-size:20px;font-weight:700;margin-top:4px">{escape(title)}</div></td></tr>
<tr><td style="padding:12px 14px 0"><table role="presentation" width="100%"><tr>{nums}</tr></table></td></tr>
<tr><td style="padding:8px 20px 4px">{blocks}</td></tr>
<tr><td style="padding:16px 20px 22px" align="center"><a href="{link}" style="background:{accent};color:#fff;text-decoration:none;padding:12px 22px;border-radius:9px;font-weight:700;display:inline-block">Open full dashboard</a></td></tr>
</table><div style="font-size:11px;color:#9ca3af;padding:10px">Prices read from public product pages. You get this because you're on the report list.</div></td></tr></table></body></html>"""


def _moves_table(moves, limit=8):
    if not moves:
        return '<p style="color:#6b7280;font-size:14px">No competitor price changes.</p>'
    rows = "".join(f'<tr><td style="padding:8px 0;border-bottom:1px solid #eee;font-size:14px">{escape(m["product"])}<div style="font-size:12px;color:#6b7280">{escape(m["competitor"])}</div></td>'
                   f'<td style="padding:8px 0;border-bottom:1px solid #eee;font-size:14px;text-align:right;white-space:nowrap">{_fmt(m["from"])} → <b>{_fmt(m["to"])}</b>'
                   f'<div style="font-size:13px;font-weight:700;color:{"#b91c1c" if m["pct"] < 0 else "#15803d"}">{"▼" if m["pct"] < 0 else "▲"} {abs(m["pct"]):.1f}%</div></td></tr>'
                   for m in moves[:limit])
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>'


def daily_html(d: dict, s: dict) -> str:
    li = lambda sev: "".join(f'<li style="margin-bottom:6px">{escape(a["message"])}</li>' for a in d["alerts"] if a["severity"] in sev)  # noqa: E731
    attention, chances = li(("high", "warn")), li(("good",))
    blocks = (f'<h3 style="font-size:15px;margin:14px 0 6px">Biggest moves</h3>{_moves_table(d["moves"])}'
              + (f'<h3 style="font-size:15px;margin:16px 0 6px;color:#b91c1c">Needs your attention</h3><ul style="padding-left:18px;font-size:14px;margin:0">{attention}</ul>' if attention else "")
              + (f'<h3 style="font-size:15px;margin:16px 0 6px;color:#15803d">Opportunities</h3><ul style="padding-left:18px;font-size:14px;margin:0">{chances}</ul>' if chances else ""))
    return _email(f"Price report for {_nice(d['day'])}: {d['changes']} changes, {d['attention']} need attention",
                  [(str(d["changes"]), "price changes", "#111827"), (str(d["cheaper"]), "where you're cheapest", "#15803d"),
                   (str(d["pricier"]), "where you're more expensive", "#b91c1c")], blocks, s["company_name"], s["accent_color"])


def weekly_html(w: dict, s: dict) -> str:
    agg = w["most_aggressive"]
    blocks = (f'<h3 style="font-size:15px;margin:14px 0 6px">Biggest price movers this week</h3>{_moves_table(w["movers"], 10)}'
              + (f'<h3 style="font-size:15px;margin:16px 0 6px">Most aggressive competitor</h3><p style="font-size:14px;margin:0">{escape(agg["competitor"])}: '
                 f'{agg["moves"]} price cuts, cheaper than you on {agg["products_undercut"]} products.</p>' if agg else "")
              + f'<h3 style="font-size:15px;margin:16px 0 6px">Your position</h3><p style="font-size:14px;margin:0">Lost position on {len(w["lost"])} products, '
                f'gained on {len(w["gained"])}.</p>')
    return _email(f"Weekly price summary · {_nice(w['start'])} – {_nice(w['day'])}",
                  [(str(w["price_changes"]), "competitor prices changed", "#111827"), (str(len(w["gained"])), "positions gained", "#15803d"),
                   (str(len(w["lost"])), "positions lost", "#b91c1c")], blocks, s["company_name"], s["accent_color"])


# --------------------------------------------------------------------------- PDF & Excel
def _pdf(path, title, subtitle, numbers, sections):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    ss = getSampleStyleSheet()
    accent = colors.HexColor(db.get_settings()["accent_color"])
    h = ParagraphStyle("h", parent=ss["Heading1"], fontSize=17, textColor=accent, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12.5, spaceBefore=10, spaceAfter=4)
    small = ParagraphStyle("s", parent=ss["BodyText"], fontSize=9, textColor=colors.HexColor("#6b7280"))
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    story = [Paragraph(escape(title), h), Paragraph(escape(subtitle), small), Spacer(1, 8)]
    nt = Table([[Paragraph(f"<b><font size=16>{escape(v)}</font></b><br/><font size=8 color='#6b7280'>{escape(l)}</font>", ss["BodyText"]) for v, l in numbers]],
               colWidths=[58 * mm] * len(numbers), hAlign="LEFT")
    nt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6f7f9")), ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
                            ("INNERGRID", (0, 0), (-1, -1), 4, colors.white), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.append(nt)
    for name, header, rows in sections:
        story.append(Paragraph(escape(name), h2))
        if not rows:
            story.append(Paragraph("Nothing to report.", small)); continue
        t = Table([header] + rows, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), accent), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                               ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f7f9")]),
                               ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(t)
    doc.build(story)


def _xlsx(path, sheets):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    wb.remove(wb.active)
    for name, header, rows in sheets:
        ws = wb.create_sheet(name[:31])
        ws.append(header)
        for c in ws[1]:
            c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="4F46E5")
        for r in rows:
            ws.append(r)
        for i, h in enumerate(header, 1):
            ws.column_dimensions[get_column_letter(i)].width = min(48, max(10, len(str(h)) + 2, *[len(str(r[i - 1] or "")) + 2 for r in rows[:200]]))
        ws.freeze_panes = "A2"
    wb.save(path)


def _store(kind, day, title, summary, html, pdf_args, sheets):
    base = REPORTS_DIR / f"{kind}_{day}"
    base.with_suffix(".html").write_text(html)
    _pdf(base.with_suffix(".pdf"), *pdf_args)
    _xlsx(base.with_suffix(".xlsx"), sheets)
    db.execute("INSERT INTO reports(kind, day, title, summary_json, html_path, pdf_path, xlsx_path, created_at) VALUES(?,?,?,?,?,?,?,?) "
               "ON CONFLICT(kind, day) DO UPDATE SET title=excluded.title, summary_json=excluded.summary_json, created_at=excluded.created_at",
               (kind, day, title, json.dumps(summary), str(base.with_suffix(".html")), str(base.with_suffix(".pdf")), str(base.with_suffix(".xlsx")), db.now()))


def build_daily(day: str):
    s = db.get_settings()
    d = daily_data(day)
    comps = db.query("SELECT id, name FROM competitors ORDER BY id")
    title = f"Price report for {_nice(day)}: {d['changes']} changes, {d['attention']} need attention"
    moves_rows = [[m["product"], m["competitor"], _fmt(m["from"]), _fmt(m["to"]), f"{m['pct']:+.1f}%"] for m in d["moves"]]
    pos_rows = [[p["sku"], p["name"], p["category"], p["price"]] + [p["competitors"].get(str(c["id"])) for c in comps] +
                [p["cheapest"], p["gap_pct"], p["position"].replace("_", " ")] for p in d["positions"]]
    _store("daily", day, title, {k: d[k] for k in ("changes", "attention", "cheaper", "pricier", "tracked")}, daily_html(d, s),
           (title, f"{s['company_name']} · {d['tracked']} products compared with {len(comps)} competitors",
            [(str(d["changes"]), "price changes"), (str(d["cheaper"]), "where you're cheapest"), (str(d["pricier"]), "where you're more expensive")],
            [("Biggest moves", ["Product", "Competitor", "Before", "Now", "Change"], moves_rows),
             ("Alerts", ["Alert"], [[a["message"]] for a in d["alerts"]])]),
           [("Positions", ["SKU", "Product", "Category", "Your price"] + [c["name"] for c in comps] + ["Cheapest competitor", "Gap %", "Position"], pos_rows),
            ("Changes", ["Product", "Competitor", "Before", "Now", "Change %"], [[m["product"], m["competitor"], m["from"], m["to"], m["pct"]] for m in d["moves"]]),
            ("Alerts", ["Type", "Message"], [[a["type"], a["message"]] for a in d["alerts"]])])


def build_weekly(day: str):
    s = db.get_settings()
    w = weekly_data(day)
    title = f"Weekly price summary · {_nice(w['start'])} – {_nice(day)}"
    agg = w["most_aggressive"]
    _store("weekly", day, title, {"price_changes": w["price_changes"], "gained": len(w["gained"]), "lost": len(w["lost"]),
                                  "most_aggressive": agg["competitor"] if agg else None}, weekly_html(w, s),
           (title, f"{s['company_name']} · most aggressive competitor: {agg['competitor'] + ' (' + str(agg['moves']) + ' price cuts)' if agg else 'none'}",
            [(str(w["price_changes"]), "competitor prices changed"), (str(len(w["gained"])), "positions gained"), (str(len(w["lost"])), "positions lost")],
            [("Biggest movers", ["Product", "Competitor", "Week start", "Now", "Change"], [[m["product"], m["competitor"], _fmt(m["from"]), _fmt(m["to"]), f"{m['pct']:+.1f}%"] for m in w["movers"]]),
             ("Where you lost position", ["Product", "Rank before", "Rank now", "Sellers"], [[x["product"], x["from"], x["to"], x["of"]] for x in w["lost"]]),
             ("Where you gained position", ["Product", "Rank before", "Rank now", "Sellers"], [[x["product"], x["from"], x["to"], x["of"]] for x in w["gained"]])]),
           [("Movers", ["Product", "Competitor", "Week start", "Now", "Change %"], [[m["product"], m["competitor"], m["from"], m["to"], m["pct"]] for m in w["movers"]]),
            ("Lost position", ["Product", "Rank before", "Rank now", "Sellers"], [[x["product"], x["from"], x["to"], x["of"]] for x in w["lost"]]),
            ("Gained position", ["Product", "Rank before", "Rank now", "Sellers"], [[x["product"], x["from"], x["to"], x["of"]] for x in w["gained"]])])


def send(report_id: int) -> str:
    """Email a report to its recipients. Without SMTP it stays in the outbox."""
    from pathlib import Path
    from . import notify
    r = db.one("SELECT * FROM reports WHERE id=?", (report_id,))
    s = db.get_settings()
    to = s["daily_recipients"] if r["kind"] == "daily" else s["weekly_recipients"]
    ok = s["channels"].get("email") and notify.send_email(to, r["title"], Path(r["html_path"]).read_text(), [Path(r["pdf_path"]), Path(r["xlsx_path"])])
    status = ", ".join(to) if ok else "outbox"
    db.execute("UPDATE reports SET sent_to=? WHERE id=?", (status, report_id))
    return status
