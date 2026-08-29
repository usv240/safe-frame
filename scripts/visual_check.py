"""Visual and behavioural acceptance for the public page.

The pytest suite asserts what the page *contains*. It cannot catch a script
that throws during initialisation and silently detaches every listener, which
is exactly what happened once: a `let` read from its temporal dead zone during
the theme restore took the whole script down, and every assertion about page
content still passed.

Two checks, in order of cheapness:

    python scripts/visual_check.py --offline
        Serves safe_frame/web with no backend and runs two passes. First every
        fetch 404s: init must complete with zero page errors, the toggles must
        respond, and the sweep must fail closed rather than throw. Then the
        endpoints are stubbed with fixtures so the whole evidence path runs --
        sweep, row selection, timeline, chart draw, caption, table view -- and
        any error thrown along it fails the check. Needs no cluster.

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


SWEEP_FIXTURE = {
    "data": {
        "regressions": [
            {"lineage_id": "title_0001", "asset_id": "title_0001__60fps_interp",
             "parent_id": "title_0001__master", "transform": "60fps_interp",
             "rule": "general_flash", "window_start_ms": 45120, "window_end_ms": 46120,
             "transitions": 7, "peak_changed_area_fraction": 0.657},
            {"lineage_id": "title_0002", "asset_id": "title_0002__subtitle_burnin",
             "parent_id": "title_0002__master", "transform": "subtitle_burnin",
             "rule": "red_flash", "window_start_ms": 96000, "window_end_ms": 97000,
             "transitions": 25, "peak_changed_area_fraction": 0.784},
        ],
        "regression_count": 2, "affected_titles": 2,
        "by_rule": {"general_flash": 1, "red_flash": 1},
        "by_transform": {"60fps_interp": 1, "subtitle_burnin": 1},
        "corpus": {"transitions": 9600000, "assets": 3200, "titles": 400, "transforms": 8},
        "timing": {"mcp_setup_ms": 0.0, "query_ms": 1710.8},
        "decision_source": "clickhouse_sql_via_official_mcp",
    }
}
SHAPE_FIXTURE = {"data": {"transitions": 9600000, "assets": 3200, "titles": 400, "transforms": 8}}


def _timeline_fixture() -> dict:
    # a clean master and a rendition that spikes once, shaped like the real data
    base = [4 if i % 3 else 5 for i in range(120)]
    child_red = [0] * 120
    child_red[96] = 25
    return {"data": {
        "parent": {"asset_id": "title_0002__master", "seconds": 120,
                   "general_flash": base, "red_flash": [0] * 120},
        "child": {"asset_id": "title_0002__subtitle_burnin", "seconds": 120,
                  "general_flash": base, "red_flash": child_red},
        "criterion_transitions_per_second": 6,
        "decision_source": "clickhouse_sql_via_official_mcp",
    }}


RISK_FIXTURE = {"data": {
    "profiles": [
        {"transform": "60fps_interp", "renditions": 400, "regressed": 16, "regressed_pct": 4.0,
         "general_flash": 16, "red_flash": 0},
        {"transform": "adbreak_insert", "renditions": 400, "regressed": 15, "regressed_pct": 3.75,
         "general_flash": 15, "red_flash": 0},
        {"transform": "subtitle_burnin", "renditions": 400, "regressed": 7, "regressed_pct": 1.75,
         "general_flash": 0, "red_flash": 7},
        {"transform": "social_crop_v", "renditions": 400, "regressed": 6, "regressed_pct": 1.5,
         "general_flash": 0, "red_flash": 6},
        {"transform": "sdr_tonemap", "renditions": 400, "regressed": 0, "regressed_pct": 0.0,
         "general_flash": 0, "red_flash": 0},
    ],
    "transforms_implicated": 4, "transforms_clean": 1, "total_regressed": 44,
    "red_only_regressions": 13, "decision_source": "clickhouse_sql_via_official_mcp",
}}
TRIAGE_FIXTURE = {"data": {
    "status": "completed", "agent": "QcTriageAgent", "model": "gemini-2.5-flash",
    "decision_source": "clickhouse_sql", "requires_human": True,
    "tool_calls": [
        {"step": 1, "tool": "survey_regressions"},
        {"step": 2, "tool": "profile_transform_risk"},
        {"step": 3, "tool": "count_luminance_blind_spot"},
        {"step": 4, "tool": "inspect_pair_timeline"},
    ],
    "steps": 4,
    "text": "\n".join([
        "What the sweep found", "44 renditions regressed.", "",
        "Systemic cause", "Two profiles.", "",
        "Required human action", "Review before release.",
    ]),
}}


def _stub(page) -> None:
    import json as _json

    def reply(route, payload):
        route.fulfill(status=200, content_type="application/json", body=_json.dumps(payload))

    page.route("**/v1/catalogue/shape", lambda r: reply(r, SHAPE_FIXTURE))
    page.route("**/v1/catalogue/sweep", lambda r: reply(r, SWEEP_FIXTURE))
    page.route("**/v1/catalogue/timeline*", lambda r: reply(r, _timeline_fixture()))
    page.route("**/v1/catalogue/transform-risk", lambda r: reply(r, RISK_FIXTURE))
    page.route("**/v1/triage", lambda r: reply(r, TRIAGE_FIXTURE))


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
        page.close()

        # second pass: stubbed endpoints, so the whole evidence path runs
        page = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
        errors2: list[str] = []
        page.on("pageerror", lambda e: errors2.append(str(e)))
        page.on("console", lambda m: errors2.append(m.text) if m.type == "error" else None)
        _stub(page)
        page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="load", timeout=30000)
        page.wait_for_timeout(800)
        page.click("#run")
        try:
            page.wait_for_selector("#rows tr[aria-selected='true']", timeout=15000)
            page.wait_for_selector("svg.timeline", timeout=15000)
        except Exception as exc:
            problems.append(f"the evidence path did not complete: {type(exc).__name__}")
        page.wait_for_timeout(600)

        # everything after the draw must have run, not just the draw itself
        if not page.eval_on_selector("#chart-cap", "e => e.textContent.trim().length > 40"):
            problems.append("the chart caption did not render after drawing")
        rows = page.eval_on_selector_all("#chart-table tr", "els => els.length")
        if rows < 100:
            problems.append(f"the chart's table view has {rows} rows, expected one per second")
        if page.eval_on_selector("#chart-empty", "e => !e.hidden"):
            problems.append("the placeholder is still showing over a drawn chart")

        # selecting the other rule must redraw rather than throw. Centre it first:
        # the header is sticky, so a row scrolled flush to the top is covered by it
        # and a real click would land on the header instead.
        row = page.locator("#rows tr:has(.chip.general_flash)").first
        row.evaluate("e => e.scrollIntoView({block: 'center'})")
        page.wait_for_timeout(200)
        row.click()
        page.wait_for_timeout(900)
        if not page.eval_on_selector_all("svg.timeline", "els => els.length"):
            problems.append("re-selecting a row left no chart")
        # the systemic-cause profile and the multi-step agent brief
        page.click("#risk-run")
        page.wait_for_timeout(900)
        bars = page.eval_on_selector_all("#risk .riskrow", "els => els.length")
        if bars != 5:
            problems.append(f"the transform profile drew {bars} rows, expected one per transform")
        if page.eval_on_selector("#outcome", "e => e.hidden"):
            problems.append("the operational outcome tiles did not appear")

        page.click("#brief-run")
        page.wait_for_timeout(900)
        steps = page.eval_on_selector_all("#trace li", "els => els.length")
        if steps != 4:
            problems.append(f"the agent trace rendered {steps} steps, expected 4")
        if page.eval_on_selector("#brief-text", "e => e.hidden"):
            problems.append("the brief did not render")
        if not page.eval_on_selector("#brief-text", "e => e.innerHTML.includes('<strong>')"):
            problems.append("the brief headings were not lifted")

        if errors2:
            problems.append(f"script threw on the evidence path: {errors2[:3]}")
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
