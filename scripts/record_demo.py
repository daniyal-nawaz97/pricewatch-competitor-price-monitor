"""Record the 2-3 minute demo video automatically (follows docs/demo-video-script.md).

Needs:  pip install playwright imageio-ffmpeg && playwright install chromium
Start the app with a fresh data folder (./run.sh), then:
    python -m scripts.record_demo --url http://localhost:8003
Output: docs/demo.mp4 and static/media/demo.webm
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent.parent
CAPTION_JS = """
(text) => {
  let el = document.getElementById('__cap');
  if (!el) {
    el = document.createElement('div'); el.id = '__cap';
    el.style.cssText = 'position:fixed;left:50%;bottom:36px;transform:translateX(-50%);z-index:2147483647;max-width:980px;' +
      'background:rgba(17,24,39,.92);color:#fff;font:600 24px/1.35 Inter,system-ui,sans-serif;padding:16px 26px;border-radius:14px;' +
      'box-shadow:0 10px 40px rgba(0,0,0,.35);text-align:center;transition:opacity .25s;pointer-events:none';
    document.body.appendChild(el);
  }
  el.style.opacity = text ? '1' : '0';
  if (text) el.innerHTML = text;
}
"""


def caption(page, text, ms=3000):
    page.evaluate(CAPTION_JS, text)
    page.wait_for_timeout(ms)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8003")
    url = ap.parse_args().url
    tmp = Path(tempfile.mkdtemp())
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome") if shutil.which("google-chrome") else p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=str(tmp), record_video_size={"width": 1280, "height": 720})
        page = ctx.new_page()
        page.goto(url + "/#/login"); page.wait_for_timeout(1200)
        caption(page, "How many competitor websites do you check each week, and how long does it take?", 4000)
        page.click("#demoBtn"); page.wait_for_timeout(2500)
        caption(page, "Every morning: how many products, how many price changes, who is cheaper, who is out of stock", 4200)
        page.mouse.wheel(0, 380); page.wait_for_timeout(600)
        caption(page, "Where you stand: cheapest, in the middle, most expensive. And today's biggest moves", 4200)
        caption(page, "", 100)
        page.goto(url + "/#/products"); page.wait_for_timeout(1800)
        caption(page, "Your price next to every competitor. Red means someone is cheaper than you", 3800)
        page.select_option("#only", "more_expensive"); page.wait_for_timeout(1500)
        caption(page, "Show only where you're more expensive, sorted by the biggest gap", 3500)
        caption(page, "", 100)
        page.goto(url + "/#/product/1"); page.wait_for_timeout(2200)
        caption(page, "Full price history for each competitor. ChargeZone just dropped this charger by 7%", 4200)
        page.mouse.wheel(0, 600); page.wait_for_timeout(700)
        caption(page, "A timeline of every change, never overwritten", 3000)
        caption(page, "", 100)
        page.goto(url + "/#/alerts"); page.wait_for_timeout(1800)
        caption(page, "Alerts: price drops, competitors undercutting you, stock-outs, new products", 3800)
        caption(page, "Your rules decide what counts, and alerts can go to WhatsApp, Telegram or email", 3500)
        caption(page, "", 100)
        page.goto(url + "/#/matches"); page.wait_for_timeout(1800)
        caption(page, "New competitor listings are matched to your products in seconds", 3200)
        page.click("[data-dec=yes]"); page.wait_for_timeout(1500)
        caption(page, "", 100)
        page.goto(url + "/#/reports"); page.wait_for_timeout(2500)
        caption(page, "The morning report: short, and made to be read on a phone", 4000)
        results = BASE / "docs" / "results.json"
        if results.exists():
            s = json.loads(results.read_text())
            caption(page, f"Demo store: {s['live_prices_correct']} of {s['live_prices_checked']} live prices read exactly right, "
                          f"{s['changes_per_week']} price changes caught in a week, about {round(s['hours_saved_per_week'])} hours of checking saved weekly", 5500)
        caption(page, "Give me 20 of your products and I'll track them free for two weeks", 4000)
        video = page.video.path()
        ctx.close(); browser.close()
    out = BASE / "static" / "media" / "demo.webm"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(video, out)
    try:
        import imageio_ffmpeg
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(video), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "23", "-movflags", "+faststart", str(BASE / "docs" / "demo.mp4")], check=True)
        print("Saved docs/demo.mp4 and static/media/demo.webm")
    except Exception as e:
        print("Saved static/media/demo.webm (mp4 skipped:", e, ")")


if __name__ == "__main__":
    main()
