#!/usr/bin/env python3
"""Real-browser smoke test for the proposed teacher workflow.

This test never touches a repository checkout. It builds an isolated local site,
starts an HTTP server, drives Chromium with Playwright, and writes screenshots
and a JSON report to the pack's reports directory.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

PACK = Path(__file__).resolve().parents[1]
PROPOSED = PACK / "proposed"
REPORTS = PACK / "reports"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return


@contextmanager
def serve(root: Path) -> Iterator[str]:
    handler = lambda *a, **kw: QuietHandler(*a, directory=str(root), **kw)  # noqa: E731
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def fixture_html(title: str, body: str, pre_script: str = "") -> str:
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} — Made by Matt</title><link rel="stylesheet" href="teacher-workflow.css"><style>body{{font-family:system-ui;margin:24px}}textarea{{display:block;width:min(640px,100%);min-height:80px;margin:8px 0}}button{{min-height:44px}}</style></head><body>{body}<script>{pre_script}</script><script defer src="teacher-workflow.js"></script></body></html>'''


def build_site(root: Path) -> None:
    for rel in [
        "Data_Manager_Studio.html", "teacher-workflow.js", "teacher-workflow.css",
        "evidence-schema-v2.json", "awarding-body-templates.json",
    ]:
        shutil.copy2(PROPOSED / rel, root / rel)
    shutil.copy2(PROPOSED / "suite-health-v2.html", root / "suite-health.html")
    (root / "favicon.ico").write_bytes(b"\x00\x00\x01\x00")
    # Estate correction C1. /hud.js is served from the domain root, not from this
    # repository -- all 28 baseline studios already reference it, and Data Manager
    # now does too. The isolated fixture site must model that root-served asset or
    # the "no console errors" assertion fails on an environment that does not
    # exist in production. The assertion itself is untouched.
    (root / "hud.js").write_text("/* estate hud stub for the fixture site */\n", encoding="utf-8")
    (root / "index.html").write_text('<!doctype html><title>Fixture Hub</title>', encoding="utf-8")

    classroom_script = r'''
window.used=[];window.keepApart=[];window.pupils=[];
window.renderTags=function(){document.getElementById("rosterStatus").textContent=document.getElementById("pickNames").value.split(/\n/).filter(Boolean).length+" names"};
window.persist=function(){localStorage.setItem("fixture.classroom.saved","1")};
'''
    (root / "Classroom_Toolkit.html").write_text(
        fixture_html(
            "Classroom Toolkit",
            '<h1>Classroom Toolkit fixture</h1><textarea id="pickNames"></textarea><textarea id="grpNames"></textarea><p id="rosterStatus"></p>',
            classroom_script,
        ), encoding="utf-8"
    )

    writing_script = r'''
window.curFrame="science";window.texts={science:["The result increased.","This supports the prediction."]};
window.frameById=function(){return {title:"Science method"}};
window.stitch=function(parts){return parts.join("\n\n")};
'''
    (root / "Writing_Frames.html").write_text(
        fixture_html(
            "Writing Frames Studio",
            '<h1>Writing fixture</h1><div class="box"><div id="previewBox">The result increased.\n\nThis supports the prediction.</div><div class="acts"><button id="copyB">Copy</button></div></div>',
            writing_script,
        ), encoding="utf-8"
    )
    (root / "Feelings_Checkin.html").write_text(
        fixture_html("Feelings Check-in", '<h1>Feelings Check-in fixture</h1><p>Private wellbeing tool.</p>'), encoding="utf-8"
    )

    apps = {
        "title": "Studio Suite fixture",
        "spaces": [
            {
                "cat": "Teacher tools",
                "items": [
                    {"f": "Data_Manager_Studio.html", "n": "Data Manager Studio", "d": "Data workflow", "i": "🧭", "c": "#2F6B4D"},
                    {"f": "Classroom_Toolkit.html", "n": "Classroom Toolkit", "d": "Roster adapter", "i": "⏲️", "c": "#c2410c"},
                ],
            },
            {
                "cat": "Learn & organise",
                "items": [
                    {"f": "Writing_Frames.html", "n": "Writing Frames Studio", "d": "Evidence hand-off", "i": "✍️", "c": "#0d9488"},
                    {"f": "Feelings_Checkin.html", "n": "Feelings Check-in", "d": "Privacy exclusion", "i": "😊", "c": "#e8b13a"},
                ],
            },
            {
                "cat": "Integration",
                "items": [
                    {"f": "https://example.invalid/official", "n": "External integration fixture", "d": "External links are reported, not fetched", "i": "🔗", "c": "#334455"}
                ],
            },
        ],
    }
    (root / "apps.json").write_text(json.dumps(apps, ensure_ascii=False, indent=2), encoding="utf-8")


def attach_errors(page: Page, errors: list[str]) -> None:
    page.on("pageerror", lambda exc: errors.append(f"pageerror {page.url}: {exc}"))
    page.on("console", lambda msg: errors.append(f"console {page.url}: {msg.text}") if msg.type == "error" else None)
    page.on("requestfailed", lambda req: errors.append(f"requestfailed {req.url}: {req.failure}"))


def check(tests: list[dict], name: str, condition: bool, detail: str) -> None:
    tests.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def click_nav(page: Page, view: str) -> None:
    page.locator(f'nav button[data-view="{view}"]').click()
    page.locator(f'[data-view-panel="{view}"]').wait_for(state="visible")


def button_heights(page: Page) -> list[float]:
    return page.locator("button:visible").evaluate_all("els => els.map(e => e.getBoundingClientRect().height)")


def run_workflow(browser: Browser, base: str, work: Path, tests: list[dict], errors: list[str]) -> Path:
    context = browser.new_context(accept_downloads=True, viewport={"width": 1365, "height": 900})
    page = context.new_page()
    attach_errors(page, errors)
    page.goto(base + "/Data_Manager_Studio.html", wait_until="networkidle")
    page.locator("#dashNotice").wait_for()
    check(tests, "Data Manager boots", "Teacher command centre" in page.locator("main").inner_text(), "dashboard rendered")

    click_nav(page, "learners")
    page.locator("#addCohortB").focus()
    page.locator("#addCohortB").click()
    page.locator("#cohortDialog").wait_for(state="visible")
    page.wait_for_function("document.activeElement && document.activeElement.id === 'cohortName'")
    focused = page.evaluate("document.activeElement && document.activeElement.id")
    check(tests, "Dialog focus enters first field", focused == "cohortName", f"focused element was {focused!r}")
    page.locator("#cohortName").fill("Year 10 Art")
    page.locator("#cohortYear").fill("2026–27")
    page.locator('#cohortForm button[type="submit"]').click()
    page.locator("#cohortDialog").wait_for(state="hidden")
    page.wait_for_timeout(80)
    returned = page.evaluate("document.activeElement && document.activeElement.id")
    check(tests, "Dialog focus returns to trigger", returned == "addCohortB", f"focus returned to {returned!r}")

    page.locator("#bulkLearnerB").click()
    page.locator("#bulkDialog").wait_for(state="visible")
    page.locator("#bulkNames").fill("L001\tAlex North\nL002\tSam Reed")
    page.locator('#bulkForm button[type="submit"]').click()
    page.locator("#bulkDialog").wait_for(state="hidden")
    page.locator("#learnerRows tr").first.wait_for()
    check(tests, "Bulk class import", page.locator("#learnerRows tr").count() == 2, "two stable learner records shown")

    page.locator("#learnerCohortFilter").select_option(label="Year 10 Art")
    page.locator("#publishRosterB").click()
    roster = page.evaluate("JSON.parse(localStorage.getItem('mbm.teacher.v1.rosters')).cohorts[0].learners.map(x=>x.displayName)")
    check(tests, "Shared roster publication", roster == ["Alex North", "Sam Reed"], f"published roster: {roster}")

    click_nav(page, "programmes")
    page.locator("#addProgrammeB").click()
    page.locator("#programmeDialog").wait_for(state="visible")
    page.locator("#programmeFramework").select_option("aqa-uas")
    page.locator("#programmeName").fill("AQA UAS Science Skills")
    # Estate correction C5. UAS records achievement: it is not a qualification and
    # has no grade and no level. The shipped fixture typed the scheme's own name
    # ("Unit Award Scheme") into the Level box, which is the exact confusion the
    # ruling corrects. That fill is not weakened away -- it is replaced by a
    # STRICTER positive control asserting the field is inert for this profile.
    check(
        tests,
        "UAS has no level (C5)",
        page.locator("#programmeLevel").is_disabled()
        and page.locator("#programmeLevel").input_value() == "",
        "Level / size is disabled and empty while the AQA UAS profile is active",
    )
    page.locator("#programmeVersion").fill("Centre copy checked August 2026")
    page.locator('#programmeForm button[type="submit"]').click()
    page.locator("#programmeDialog").wait_for(state="hidden")
    page.locator("[data-new-unit]").click()
    page.locator("#unitDialog").wait_for(state="visible")
    page.locator("#unitCode").fill("SCI-001")
    page.locator("#unitName").fill("Plan and review a practical")
    page.locator("#unitSource").fill("Current centre unit document")
    page.locator("#unitCriteria").fill("1 | Plans a fair test | Written plan or observation\n2 | Reviews results using evidence | Learner review and data")
    page.locator('#unitForm button[type="submit"]').click()
    page.locator("#unitDialog").wait_for(state="hidden")
    check(tests, "Programme and criterion setup", page.locator(".criterion").count() == 2, "two coded criteria rendered")

    click_nav(page, "evidence")
    page.locator('#evidenceView [data-action="new-evidence"]').click()
    page.locator("#evidenceDialog").wait_for(state="visible")
    for checkbox in page.locator("#evLearners input").all():
        checkbox.check()
    page.locator("#evUnit").select_option(index=1)
    page.locator("#evCriteria input").first.check()
    page.locator("#evRecordTitle").fill("Practical planning evidence")
    page.locator("#evNote").fill("Both learners identified variables and recorded a plan. Staff review is still required.")
    page.locator("#evAssessor").fill("M. Roper")
    page.locator("#evDecision").select_option("not-assessed")
    page.locator("#evIndependence").select_option("supported")
    attachment = work / "planning-note.txt"
    attachment.write_text("Fixture evidence attachment", encoding="utf-8")
    page.locator("#evFiles").set_input_files(str(attachment))
    page.locator('#evidenceForm button[type="submit"]').click()
    page.locator("#evidenceDialog").wait_for(state="hidden", timeout=15000)
    page.locator("#evidenceRows tr").first.wait_for()
    check(tests, "Evidence with hashed attachment", page.locator("#evidenceRows tr").count() == 1 and "1" in page.locator("#evidenceRows tr").first.inner_text(), "one evidence record saved with one attachment")

    click_nav(page, "coverage")
    page.locator("#coverageUnitSel").select_option(index=1)
    page.locator("#coverageCohortSel").select_option(label="Year 10 Art")
    page.locator("#coverageBody tr").first.wait_for()
    check(tests, "Coverage matrix", page.locator("#coverageBody tr").count() == 2 and page.locator("#coverageHead th").count() == 3, "two learners by two criteria rendered")

    click_nav(page, "exports")
    with page.expect_download(timeout=15000) as info:
        page.locator("#backupB").click()
    download = info.value
    backup_path = work / download.suggested_filename
    download.save_as(str(backup_path))
    page.wait_for_function("document.querySelector('#backupBanner').textContent.includes('Backup is current')")
    payload = json.loads(backup_path.read_text(encoding="utf-8"))
    state = payload["state"]
    attachment_data = payload["attachmentData"]
    valid_backup = (
        payload.get("format") == "made-by-matt-data-manager-backup"
        and len(state.get("learners", [])) == 2
        and len(state.get("evidence", [])) == 1
        and len(state.get("attachments", [])) == 1
        and len(attachment_data) == 1
        and len(state["attachments"][0].get("hash", "")) == 64
    )
    check(tests, "Full backup integrity", valid_backup, "backup contains 2 learners, 1 evidence record, attachment bytes and SHA-256")

    heights = button_heights(page)
    check(tests, "44px visible controls", bool(heights) and min(heights) >= 43.5, f"minimum visible button height {min(heights):.1f}px")

    click_nav(page, "dashboard")
    page.screenshot(path=str(REPORTS / "data-manager-desktop.png"), full_page=True)
    page.reload(wait_until="networkidle")
    click_nav(page, "learners")
    check(tests, "IndexedDB reload persistence", page.locator("#learnerRows tr").count() == 2, "two learners remained after reload")

    classroom = context.new_page()
    attach_errors(classroom, errors)
    classroom.goto(base + "/Classroom_Toolkit.html", wait_until="networkidle")
    classroom.locator("#mbm-teacher-launcher").click()
    classroom.locator("#mbm-teacher-dialog").wait_for(state="visible")
    classroom.locator("#mbm-use-roster").click()
    pick = classroom.locator("#pickNames").input_value().splitlines()
    groups = classroom.locator("#grpNames").input_value().splitlines()
    check(tests, "Classroom Toolkit roster adapter", pick == roster and groups == roster, f"picker/groups received {pick}")

    writing = context.new_page()
    attach_errors(writing, errors)
    writing.goto(base + "/Writing_Frames.html", wait_until="networkidle")
    writing.locator("[data-mbm-handoff]").click()
    outbox = writing.evaluate("JSON.parse(localStorage.getItem('mbm.teacher.v1.outbox')).records")
    check(tests, "Writing evidence hand-off", len(outbox) == 1 and outbox[0]["recordType"] == "learner-evidence" and "supports the prediction" in outbox[0]["evidence"]["note"], "draft queued without an automatic assessment decision")

    feelings = context.new_page()
    attach_errors(feelings, errors)
    feelings.goto(base + "/Feelings_Checkin.html", wait_until="networkidle")
    check(tests, "Wellbeing privacy exclusion", feelings.locator("#mbm-teacher-launcher").count() == 0 and feelings.locator("[data-mbm-handoff]").count() == 0, "no teacher context or evidence launcher appears")

    health = context.new_page()
    attach_errors(health, errors)
    health.goto(base + "/suite-health.html", wait_until="networkidle")
    health.locator("#runB").click()
    health.wait_for_function("document.querySelector('#live').textContent.includes('Check complete')")
    fails = int(health.locator(".stat.fail b").inner_text())
    check(tests, "Suite Health v2", fails == 0 and health.locator("#catalogueRows tr").count() == 5, "catalogue and five upgrade assets pass; external target is informational")

    context.close()
    return backup_path


def restore_and_mobile(browser: Browser, base: str, backup_path: Path, tests: list[dict], errors: list[str]) -> None:
    context = browser.new_context(accept_downloads=True, viewport={"width": 1100, "height": 820})
    page = context.new_page()
    attach_errors(page, errors)
    page.goto(base + "/Data_Manager_Studio.html", wait_until="networkidle")
    click_nav(page, "exports")
    page.locator("#restoreFile").set_input_files(str(backup_path))
    page.locator("#restoreDialog").wait_for(state="visible")
    page.locator("#mergeRestoreB").click()
    page.locator("#restoreDialog").wait_for(state="hidden", timeout=15000)
    click_nav(page, "learners")
    learners = page.locator("#learnerRows tr").count()
    click_nav(page, "evidence")
    evidence = page.locator("#evidenceRows tr").count()
    page.locator("[data-edit-evidence]").first.click()
    page.locator("#evidenceDialog").wait_for(state="visible")
    attachment_visible = "planning-note.txt" in page.locator("#existingFiles").inner_text()
    page.locator("#evidenceDialog [data-close]").first.click()
    check(tests, "Fresh-context backup restore", learners == 2 and evidence == 1 and attachment_visible, "learners, evidence metadata and attachment blob restored")

    page.set_viewport_size({"width": 390, "height": 844})
    click_nav(page, "dashboard")
    page.screenshot(path=str(REPORTS / "data-manager-mobile.png"), full_page=True)
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    heights = button_heights(page)
    check(tests, "Mobile layout and targets", overflow <= 1 and min(heights) >= 43.5, f"horizontal overflow {overflow}px; minimum button {min(heights):.1f}px")
    context.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--browser-executable", default="", help="optional Chromium/Chrome executable; blank uses Playwright bundled Chromium")
    args = ap.parse_args()
    REPORTS.mkdir(parents=True, exist_ok=True)
    tests: list[dict] = []
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="mbm-browser-smoke-") as td:
        root = Path(td) / "site"
        root.mkdir()
        build_site(root)
        with serve(root) as base, sync_playwright() as pw:
            launch_args={"headless":True,"args":["--no-sandbox","--disable-gpu"]}
            if args.browser_executable: launch_args["executable_path"]=args.browser_executable
            browser = pw.chromium.launch(**launch_args)
            try:
                backup = run_workflow(browser, base, Path(td), tests, errors)
                restore_and_mobile(browser, base, backup, tests, errors)
            finally:
                browser.close()

    check(tests, "Browser console and network", not errors, "no console errors, page errors or failed requests" if not errors else "; ".join(errors))
    report = {
        "format": "made-by-matt-teacher-upgrade-browser-smoke",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "browserExecutable": args.browser_executable or "Playwright bundled Chromium",
        "summary": {
            "pass": sum(1 for x in tests if x["status"] == "pass"),
            "fail": sum(1 for x in tests if x["status"] == "fail"),
        },
        "tests": tests,
        "errors": errors,
    }
    (REPORTS / "BROWSER_SMOKE_RESULTS.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    for item in tests:
        print(f"{item['status'].upper():4} {item['name']}: {item['detail']}")
    return 1 if report["summary"]["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
