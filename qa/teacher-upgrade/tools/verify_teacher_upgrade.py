#!/usr/bin/env python3
"""Verify an applied Made by Matt teacher-workflow upgrade checkout."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

BASELINE_FILES = [
    "404.html", "Animation_Studio.html", "Art_Studio.html", "Audio_Studio.html",
    "ChoreoStudio.html", "Classroom_Toolkit.html", "Comic_Studio.html",
    "Craft_Studio.html", "Design_Studio.html", "Evidence_Binder.html",
    "Exit_Ticket.html", "Feelings_Checkin.html", "Graph_Studio.html",
    "Message_Studio.html", "Mindmap_Studio.html", "Music_Studio.html",
    "NowNext_Board.html", "PDF_Studio.html", "Photo_Studio.html",
    "Quiz_Studio.html", "README.md", "Regulation_Station.html",
    "Rubric_Studio.html", "Seating_Studio.html", "Typing_Tutor.html",
    "Video_Studio.html", "Web_Studio.html", "Whiteboard.html",
    "Writing_Frames.html", "apps.json", "index.html", "studio-bg.svg",
    "studio-suite-creative-lab.png", "suite-health.html",
]
ADDED = [
    "Data_Manager_Studio.html", "teacher-workflow.js", "teacher-workflow.css",
    "evidence-schema-v2.json", "awarding-body-templates.json",
]
TARGETS = [
    "Evidence_Binder.html", "Classroom_Toolkit.html", "Seating_Studio.html",
    "Rubric_Studio.html", "Exit_Ticket.html", "Writing_Frames.html",
    "Quiz_Studio.html", "Graph_Studio.html", "Whiteboard.html", "PDF_Studio.html",
    "ChoreoStudio.html",
]
EXCLUDED = ["Feelings_Checkin.html", "Regulation_Station.html"]


@dataclass
class Finding:
    status: str
    check: str
    detail: str


class TagCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.external_runtime: list[str] = []
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        ref = values.get("src") if tag in {"script", "img", "iframe", "audio", "video", "source"} else values.get("href") if tag == "link" else None
        if ref and urlparse(ref).scheme in {"http", "https"}:
            self.external_runtime.append(ref)


def node_check(code: str, label: str) -> tuple[bool, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as fh:
        fh.write(code)
        path = Path(fh.name)
    try:
        p = subprocess.run(["node", "--check", str(path)], text=True, capture_output=True)
        return p.returncode == 0, (p.stderr or p.stdout).strip()
    except FileNotFoundError:
        return False, "Node.js is unavailable"
    finally:
        path.unlink(missing_ok=True)


def extract_inline_scripts(html: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.I | re.S)]


def validate(root: Path) -> list[Finding]:
    out: list[Finding] = []

    def add(ok: bool, check: str, good: str, bad: str, warn: bool = False) -> None:
        out.append(Finding("pass" if ok else ("warn" if warn else "fail"), check, good if ok else bad))

    missing_baseline = [f for f in BASELINE_FILES if not (root / f).exists()]
    add(not missing_baseline, "non-destructive baseline", "all 34 audited source artefacts remain", "missing audited source artefacts: " + ", ".join(missing_baseline))
    missing_added = [f for f in ADDED if not (root / f).is_file()]
    add(not missing_added, "upgrade files", "all five upgrade-owned files are present", "missing upgrade files: " + ", ".join(missing_added))

    for rel in TARGETS:
        p = root / rel
        if not p.exists():
            out.append(Finding("fail", f"workflow integration: {rel}", "file missing"))
            continue
        text = p.read_text(encoding="utf-8")
        ok = text.count("mbm-teacher-workflow:v1") == 1 and text.count('src="teacher-workflow.js"') == 1 and text.count('href="teacher-workflow.css"') == 1
        add(ok, f"workflow integration: {rel}", "one additive CSS and JS integration", "integration is missing or duplicated")

    for rel in EXCLUDED:
        p = root / rel
        if p.exists():
            text = p.read_text(encoding="utf-8")
            add("teacher-workflow.js" not in text and "mbm-teacher-workflow:v1" not in text, f"privacy exclusion: {rel}", "no evidence/workflow bridge injected", "sensitive wellbeing tool contains teacher workflow bridge")

    evidence = (root / "Evidence_Binder.html").read_text(encoding="utf-8") if (root / "Evidence_Binder.html").exists() else ""
    add(evidence.count("mbm-outcome-id-safety:v1") == 1, "Evidence Binder criterion identity", "stable-ID reorder guard present once", "stable-ID guard missing or duplicated")
    add(evidence.count("mbm-unit-delete-safety:v1") == 1 and "stay stored but lose their unit tags" not in evidence, "Evidence Binder linked-unit deletion", "linked evidence cannot be silently orphaned", "old orphaning path remains or guard is missing")

    try:
        apps = json.loads((root / "apps.json").read_text(encoding="utf-8"))
        items = [it for space in apps.get("spaces", []) for it in space.get("items", [])]
        names = [it.get("n") for it in items]
        files = [it.get("f") for it in items]
        add(bool(items), "catalogue cardinality", f"{len(items)} catalogue entries loaded", "catalogue is empty")
        add(len(names) == len(set(names)), "catalogue unique names", "studio names are unique", "duplicate studio names found")
        manager = [it for it in items if it.get("n") == "Data Manager Studio"]
        add(len(manager) == 1 and manager[0].get("f") == "Data_Manager_Studio.html", "Data Manager catalogue entry", "one exact local catalogue entry", "Data Manager entry missing, duplicated or points elsewhere")
        missing_local = [f for f in files if isinstance(f, str) and not re.match(r"^https?://", f) and not (root / f).is_file()]
        add(not missing_local, "catalogue local targets", "every local catalogue target exists", "missing local catalogue targets: " + ", ".join(missing_local))
    except Exception as exc:
        out.append(Finding("fail", "apps.json", f"could not parse: {exc}"))

    index = (root / "index.html").read_text(encoding="utf-8") if (root / "index.html").exists() else ""
    add("28 single-file studios" not in index, "hub count drift", "stale hard-coded count removed", "old 28-studio claim remains")
    add(index.count('"Data Manager Studio":"t"') == 1, "hub audience mapping", "Data Manager classified as teacher admin", "Data Manager audience mapping missing or duplicated")

    readme = (root / "README.md").read_text(encoding="utf-8") if (root / "README.md").exists() else ""
    add("Suite_Hub.html" not in readme and "Data Manager Studio" in readme, "README current entry point", "README uses index.html and documents Data Manager", "README retains stale hub or omits Data Manager")
    add("Evidence and awarding-body boundary" in readme and "not encrypted by the app" in readme, "README evidence guardrails", "assessment and backup boundaries documented", "evidence or backup guardrails missing")

    health = (root / "suite-health.html").read_text(encoding="utf-8") if (root / "suite-health.html").exists() else ""
    add("apps.json" in health and 'const re=/f:' not in health, "suite health catalogue source", "health checker reads apps.json rather than retired inline records", "health checker still uses retired inline record regex")
    add("catalogue is empty" in health.lower() or "empty catalogue" in health.lower(), "suite health positive control", "empty catalogue is treated as a failure", "no explicit empty-catalogue failure found")

    for rel in ["evidence-schema-v2.json", "awarding-body-templates.json"]:
        try:
            data = json.loads((root / rel).read_text(encoding="utf-8"))
            add(True, f"JSON parse: {rel}", "valid JSON", "")
            if rel == "evidence-schema-v2.json":
                add(data.get("title") == "Made by Matt teacher evidence interchange record" and data.get("properties", {}).get("schemaVersion", {}).get("const") == 2, "evidence schema identity", "schema v2 identity and fixed version are present", "schema identity/version is unexpected")
            else:
                ids = {x.get("id") for x in data.get("profiles", [])}
                required = {"generic-portfolio", "aqa-uas", "asdan-short-course", "asdan-peq", "arts-award"}
                add(required.issubset(ids), "framework profiles", "generic portfolio, AQA UAS, ASDAN Short Course, ASDAN PEQ and Arts Award profiles present", "missing profiles: " + ", ".join(sorted(required - ids)))
        except Exception as exc:
            out.append(Finding("fail", f"JSON parse: {rel}", str(exc)))

    for rel in ["Data_Manager_Studio.html", "suite-health.html"]:
        p = root / rel
        if not p.exists():
            continue
        html = p.read_text(encoding="utf-8")
        parser = TagCollector()
        try:
            parser.feed(html)
            add(not parser.external_runtime, f"offline runtime: {rel}", "no external runtime assets", "external runtime assets: " + ", ".join(parser.external_runtime))
            duplicates = sorted({i for i in parser.ids if parser.ids.count(i) > 1})
            add(not duplicates, f"unique IDs: {rel}", "HTML IDs are unique", "duplicate IDs: " + ", ".join(duplicates))
        except Exception as exc:
            out.append(Finding("fail", f"HTML parse: {rel}", str(exc)))
        scripts = extract_inline_scripts(html)
        for idx, script in enumerate(scripts, 1):
            ok, detail = node_check(script, f"{rel} inline script {idx}")
            add(ok, f"JavaScript syntax: {rel} #{idx}", "Node syntax check passed", detail or "Node syntax check failed")

    js = (root / "teacher-workflow.js").read_text(encoding="utf-8") if (root / "teacher-workflow.js").exists() else ""
    ok, detail = node_check(js, "teacher-workflow.js") if js else (False, "file missing")
    add(ok, "JavaScript syntax: teacher-workflow.js", "Node syntax check passed", detail or "Node syntax check failed")
    add("Feelings" in js and "Regulation" in js and "excluded" in js, "workflow privacy deny-list", "wellbeing tools are explicitly excluded", "wellbeing deny-list not found")
    add("ps_coldcall_roster" in js and "mbm.teacher.v1.rosters" in js, "roster compatibility", "legacy lesson roster and versioned shared roster are supported", "roster compatibility keys missing")

    dm = (root / "Data_Manager_Studio.html").read_text(encoding="utf-8") if (root / "Data_Manager_Studio.html").exists() else ""
    add("user-scalable=no" not in dm, "zoom accessibility", "page zoom is not disabled", "viewport disables zoom")
    add(bool(re.search(r"button\{[^}]*min-height:44px", dm)) and "min-height:44px" in (root / "teacher-workflow.css").read_text(encoding="utf-8"), "touch targets", "Data Manager and workflow controls specify 44px minimum targets", "44px minimum target contract not found")
    add("prefers-reduced-motion" in dm and "prefers-reduced-motion" in (root / "teacher-workflow.css").read_text(encoding="utf-8"), "reduced motion", "both new visual layers respect reduced motion", "reduced-motion handling missing")
    add("not encrypted" in dm.lower() and "no automatic uploads" in dm.lower(), "Data Manager privacy copy", "local-only and unencrypted-backup boundaries are visible", "privacy boundary copy missing")

    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.repo).expanduser().resolve()
    findings = validate(root)
    counts = {s: sum(1 for f in findings if f.status == s) for s in ["pass", "warn", "fail"]}
    payload = {"repository": str(root), "summary": counts, "findings": [asdict(f) for f in findings]}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for f in findings:
            print(f"{f.status.upper():4} {f.check}: {f.detail}")
        print(f"\n{counts['pass']} passed, {counts['warn']} warnings, {counts['fail']} failures")
    return 1 if counts["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
