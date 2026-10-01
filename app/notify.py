"""Deliver alerts and reports by email, Telegram or WhatsApp. Every channel is optional.

Without SMTP settings, emails are kept in the app's Reports outbox (nothing is lost, nothing is sent).
"""
from __future__ import annotations

import json
import logging
import smtplib
import urllib.request
from email.message import EmailMessage
from pathlib import Path

from . import db
from .config import (PUBLIC_BASE_URL, SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER, TELEGRAM_BOT_TOKEN, WHATSAPP_PHONE_ID,
                     WHATSAPP_TOKEN)

log = logging.getLogger("pricewatch.notify")


def channels_status() -> dict:
    return {"email": bool(SMTP_HOST), "telegram": bool(TELEGRAM_BOT_TOKEN), "whatsapp": bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID)}


def send_email(to: list[str], subject: str, html: str, attachments: list[Path] = ()) -> bool:
    if not SMTP_HOST or not to:
        return False
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, SMTP_FROM, ", ".join(to)
    msg.set_content("Open this email in an HTML-capable mail app to see the report.")
    msg.add_alternative(html, subtype="html")
    for a in attachments:
        if a and Path(a).exists():
            sub = "pdf" if str(a).endswith(".pdf") else "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            msg.add_attachment(Path(a).read_bytes(), maintype="application", subtype=sub, filename=Path(a).name)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
            s.starttls()
            if SMTP_USER:
                s.login(SMTP_USER, SMTP_PASSWORD)
            s.send_message(msg)
        return True
    except Exception as e:
        log.warning("email failed: %s", e)
        return False


def send_telegram(chat_id: str, text: str) -> bool:
    if not (TELEGRAM_BOT_TOKEN and chat_id):
        return False
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", method="POST",
                                     data=json.dumps({"chat_id": chat_id, "text": text, "disable_web_page_preview": True}).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=20).read()
        return True
    except Exception as e:
        log.warning("telegram failed: %s", e)
        return False


def send_whatsapp(to: str, text: str) -> bool:
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_ID and to):
        return False
    try:
        req = urllib.request.Request(f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/messages", method="POST",
                                     data=json.dumps({"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[:4000]}}).encode(),
                                     headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=20).read()
        return True
    except Exception as e:
        log.warning("whatsapp failed: %s", e)
        return False


def alerts_digest(day: str):
    """Send today's important alerts as one short message on the enabled chat channels."""
    s = db.get_settings()
    rows = db.query("SELECT * FROM alerts WHERE day=? AND delivered IS NULL AND severity IN ('high','warn','good') ORDER BY id", (day,))
    if not rows:
        return
    lines = [f"PriceWatch · {len(rows)} alert{'s' if len(rows) > 1 else ''} today"] + [f"• {r['message']}" for r in rows[:12]]
    if PUBLIC_BASE_URL:
        lines.append(f"\nOpen dashboard: {PUBLIC_BASE_URL}/#/alerts")
    text = "\n".join(lines)
    sent = []
    if s["channels"].get("telegram") and send_telegram(s.get("telegram_chat_id", ""), text):
        sent.append("telegram")
    if s["channels"].get("whatsapp") and send_whatsapp(s.get("whatsapp_to", ""), text):
        sent.append("whatsapp")
    db.execute(f"UPDATE alerts SET delivered=? WHERE id IN ({','.join('?' * len(rows))})", (",".join(sent) or "in_app", *[r["id"] for r in rows]))
