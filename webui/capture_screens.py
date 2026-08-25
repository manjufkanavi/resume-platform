"""Capture screenshots of every Resume Platform page via Playwright.

Usage:
    python3 capture_screens.py        # launch dev/start server on 3007 first

Screens are saved to ./screenshots/*.png.
Two contexts: a public one (landing/login/signup/templates) and a demo-authenticated
one (dashboard/resume detail/upload) obtained by clicking "Try Demo".
"""
import sys, os, time
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3007")
OUT = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(OUT, exist_ok=True)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ---- public pages ----
        pub = browser.new_context(viewport={"width": 1440, "height": 900})
        pub_screens = [
            ("/", "01_landing"),
            ("/login", "02_login"),
            ("/signup", "03_signup"),
            ("/templates", "04_templates"),
        ]
        for path, tag in pub_screens:
            page = pub.new_page()
            goto(page, f"{BASE}{path}", tag)
            page.close()

        # ---- demo-authenticated pages ----
        auth = browser.new_context(viewport={"width": 1440, "height": 900})
        page = auth.new_page()
        goto(page, f"{BASE}/", "01_landing")  # logged-out (redundant w/ public)
        click(page, 'text="Try Demo"')
        goto(page, f"{BASE}/dashboard", "05_dashboard")
        # open a resume detail
        goto(page, f"{BASE}/resume/demo-1", "06_resume_detail")
        goto(page, f"{BASE}/upload", "07_upload")
        page.close()

        browser.close()
        print(f"Done. Saved to {OUT}")


def goto(page, url, tag):
    page.goto(url, wait_until="networkidle", timeout=30000)
    time.sleep(1.2)  # let animations/LOss settle
    ext = "pre" if tag.startswith("pre") else "png"
    path = os.path.join(OUT, f"{tag}.{ext}")
    page.screenshot(path=path)
    print(f"  -> {path}")


def click(page, selector):
    page.eval_on_selector(selector, "el => el.click()")
    time.sleep(1.0)


if __name__ == "__main__":
    main()
