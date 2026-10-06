#!/usr/bin/env python3
"""Screenshot each club's Playtomic page and log the result.

Usage:  python capture.py
Reads clubs.json (same folder). Saves screenshots/<club>_<YYYY-MM-DD_HHMM>.png,
a text dump of the page next to it, and appends a row to log.csv.
"""
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

TZ = ZoneInfo("Europe/Dublin")
BASE = Path(__file__).parent
OUT = BASE / "screenshots"
LOG = BASE / "log.csv"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def dismiss_cookies(page):
    for label in ("Accept all", "Accept All", "Accept", "I agree", "Allow all"):
        try:
            page.get_by_role("button", name=label).first.click(timeout=1500)
            return
        except Exception:
            pass


def main():
    OUT.mkdir(exist_ok=True)
    clubs = json.loads((BASE / "clubs.json").read_text())
    clubs = [c for c in clubs if c.get("url") and "TODO" not in c["url"]]
    stamp = datetime.now(TZ).strftime("%Y-%m-%d_%H%M")
    new_log = not LOG.exists()

    with sync_playwright() as p, LOG.open("a", newline="") as f:
        writer = csv.writer(f)
        if new_log:
            writer.writerow(["timestamp_dublin", "club", "url", "status", "screenshot"])
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 2000},
            locale="en-IE",
            timezone_id="Europe/Dublin",
        )
        for club in clubs:
            name, url = club["name"], club["url"]
            shot = OUT / f"{slug(name)}_{stamp}.png"
            status = "ok"
            try:
                page = ctx.new_page()
                page.goto(url, wait_until="networkidle", timeout=45000)
                dismiss_cookies(page)
                page.wait_for_timeout(4000)  # let the availability grid render
                zoom = club.get("zoom")  # e.g. 0.5 shows the page at 50%
                if zoom:
                    page.evaluate(f"document.body.style.zoom = '{zoom}'")
                    page.wait_for_timeout(1500)
                page.screenshot(path=str(shot), full_page=True)
                shot.with_suffix(".txt").write_text(page.inner_text("body"))
                page.close()
            except Exception as e:  # keep going if one club fails
                status = f"error: {type(e).__name__}"
                shot = ""
            writer.writerow(
                [datetime.now(TZ).isoformat(timespec="seconds"), name, url, status, shot]
            )
            print(f"{name}: {status}")
        browser.close()


if __name__ == "__main__":
    main()
