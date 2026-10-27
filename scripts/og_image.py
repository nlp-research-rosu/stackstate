"""Render site/og.png (1200x630), the link-preview image, from the top of site/index.html.

Needs Playwright (pip install playwright) and Google Chrome, or Playwright's own Chromium
(python -m playwright install chromium).
"""
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome")  # preinstalled on GitHub's Ubuntu runners
    except Exception:
        browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1200, "height": 630})
    page.goto((ROOT / "site" / "index.html").as_uri())  # uses the data embedded in the page
    page.wait_for_timeout(1500)
    page.screenshot(path=str(ROOT / "site" / "og.png"))
    browser.close()
print("wrote site/og.png")
