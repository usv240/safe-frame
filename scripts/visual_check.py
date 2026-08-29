"""Visual and behavioural acceptance for the public page.

The pytest suite asserts what the page *contains*. It cannot catch a script
that throws during initialisation and silently detaches every listener, which
is exactly what happened once: a `let` read from its temporal dead zone during
the theme restore took the whole script down, and every assertion about page
content still passed.

Two checks, in order of cheapness:

    python scripts/visual_check.py --offline
        Serves safe_frame/web with no backend at all, so every fetch 404s.
        Init must complete with zero page errors, the toggles must respond, and
        the sweep must fail closed rather than throw. Needs no cluster.

    python scripts/visual_check.py --url https://<deployment>/
        Drives the real judge path against a deployment: sweep, row selection,
        evidence chart, red-flash row. Screenshots both themes at phone, laptop
        and desktop widths, and fails on horizontal overflow or console errors.

Requires `playwright` and `python -m playwright install chromium`.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WEB = REPO / "safe_frame" / "web"
SIZES = [("phone", 390, 844), ("laptop", 1280, 800), ("desktop", 1680, 1050)]


def offline() -> list[str]:
    from playwright.sync_api import sync_playwright

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(WEB))
    handler.log_message = lambda *a, **k: None  # type: ignore[assignment]
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    problems: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="load", timeout=30000)
        page.wait_for_timeout(1200)
        if errors:
            problems.append(f"script threw during init: {errors}")

        page.click("#t-dark")
        if page.evaluate("() => document.documentElement.dataset.theme") != "dark":
            problems.append("dark toggle did not stamp the root element")
        page.click("#t-light")
        if page.evaluate("() => document.documentElement.dataset.theme") != "light":
            problems.append("light toggle did not stamp the root element")
        page.click("#m-tech")
        if not page.evaluate("() => document.body.classList.contains('tech')"):
            problems.append("technical mode toggle is not wired")

        page.click("#run")
        page.wait_for_timeout(1500)
        if "failed closed" not in page.eval_on_selector("#sweeptitle", "e => e.textContent"):
            problems.append("a failing sweep did not report failing closed")
        if errors:
            problems.append(f"script threw during interaction: {errors}")
        browser.close()
    server.shutdown()
    return problems


def live(url: str, out: Path) -> list[str]:
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for theme in ("light", "dark"):
            for name, w, h in SIZES:
                ctx = browser.new_context(viewport={"width": w, "height": h},
                                          color_scheme=theme, device_scale_factor=2)
                page = ctx.new_page()
                errors: list[str] = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
                page.goto(url, wait_until="networkidle", timeout=90000)

                over = page.evaluate(
                    "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
                if over > 1:
                    problems.append(f"{theme}/{name}: page scrolls horizontally by {over}px")
                page.screenshot(path=str(out / f"{theme}-{name}.png"))

                if name == "laptop":
                    page.click("#run")
                    page.wait_for_selector("#rows tr[aria-selected='true']", timeout=120000)
                    page.wait_for_selector("svg.timeline", timeout=120000)
                    page.locator("#evidence").scroll_into_view_if_needed()
                    page.wait_for_timeout(600)
                    page.screenshot(path=str(out / f"{theme}-evidence.png"))
                    red = page.locator("#rows tr:has(.chip.red_flash)").first
                    if red.count():
                        red.click()
                        page.wait_for_selector("svg.timeline", timeout=60000)
                        page.wait_for_timeout(900)
                        page.locator("#evidence").scroll_into_view_if_needed()
                        page.screenshot(path=str(out / f"{theme}-redflash.png"))
                    else:
                        problems.append(f"{theme}: no red_flash row in the sweep to inspect")
                    over = page.evaluate(
                        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
                    if over > 1:
                        problems.append(f"{theme}/{name}: horizontal overflow {over}px after the sweep")

                if errors:
                    problems.append(f"{theme}/{name}: console errors {errors[:3]}")
                ctx.close()

        # the chart must repaint correctly on the narrowest supported width
        ctx = browser.new_context(viewport={"width": 390, "height": 844},
                                  color_scheme="dark", device_scale_factor=2)
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=90000)
        page.click("#run")
        page.wait_for_selector("svg.timeline", timeout=120000)
        page.locator("#evidence").scroll_into_view_if_needed()
        page.wait_for_timeout(800)
        page.screenshot(path=str(out / "dark-phone-evidence.png"))
        over = page.evaluate(
            "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        if over > 1:
            problems.append(f"dark/phone: horizontal overflow {over}px after the sweep")
        ctx.close()
        browser.close()
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="init check, no backend needed")
    ap.add_argument("--url", help="drive the judge path against a deployment")
    ap.add_argument("--out", default=str(REPO / "build" / "shots"), help="screenshot directory")
    args = ap.parse_args()
    if not args.offline and not args.url:
        args.offline = True

    problems: list[str] = []
    if args.offline:
        problems += offline()
    if args.url:
        problems += live(args.url, Path(args.out))

    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("no init, layout, overflow or console problems found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
