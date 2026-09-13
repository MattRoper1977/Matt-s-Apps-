#!/usr/bin/env python3
"""Non-destructive installer for the Made by Matt teacher workflow upgrade.

Default behaviour is a read-only dry run. Existing files are never removed. On
--apply, every changed existing file is copied to a timestamped sibling backup
before atomic replacement. New files are added only.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

PACK_ROOT = Path(__file__).resolve().parents[1]
PROPOSED = PACK_ROOT / "proposed"
BASELINE_HEAD = "c69895423ecaaf4fa859bd6fef6bc717d2a94863"

BASELINE_SHA1 = {
    "Evidence_Binder.html": "b4480bb72bb5a8ac13fc518ea75ec412b47098c7",
    "Classroom_Toolkit.html": "39a7990a3e42fe7cec14ac41777d38f2cd68d223",
    "Seating_Studio.html": "15eab003dd2529f725fc6f9c2bd811508f3b6662",
    "Rubric_Studio.html": "2d08e1d089b90e271a878a272772ab94886ccc93",
    "Exit_Ticket.html": "beb4b2150c37f80605620ddad673830a0ec1991e",
    "Writing_Frames.html": "950b44268fa457c3dbcd8e3595ea302dd02e79c6",
    "apps.json": "86738f6b0762737b8a67ffa84d4f60a8a88c55a1",
    "index.html": "8b2e0369f36f1422c3b7d05ef921f0261a9a057e",
    "README.md": "e8bb1e21d80c0f8f87c3a7d2ededda2fd88829d8",
    "suite-health.html": "c8336ad5bf983f3dae2834b96cfb612acf327dfb",
}

REQUIRED_REPO_FILES = [
    "index.html",
    "apps.json",
    "README.md",
    "suite-health.html",
    "Evidence_Binder.html",
    "Classroom_Toolkit.html",
    "Seating_Studio.html",
    "Rubric_Studio.html",
    "Exit_Ticket.html",
    "Writing_Frames.html",
    "Quiz_Studio.html",
    "Graph_Studio.html",
    "Whiteboard.html",
    "PDF_Studio.html",
    "ChoreoStudio.html",
]

COPY_FILES = [
    "Data_Manager_Studio.html",
    "teacher-workflow.js",
    "teacher-workflow.css",
    "evidence-schema-v2.json",
    "awarding-body-templates.json",
]

WORKFLOW_TARGETS = [
    "Evidence_Binder.html",
    "Classroom_Toolkit.html",
    "Seating_Studio.html",
    "Rubric_Studio.html",
    "Exit_Ticket.html",
    "Writing_Frames.html",
    "Quiz_Studio.html",
    "Graph_Studio.html",
    "Whiteboard.html",
    "PDF_Studio.html",
    "ChoreoStudio.html",
]

WORKFLOW_HEAD_MARKER = "<!-- mbm-teacher-workflow:v1 -->"
WORKFLOW_SCRIPT_MARKER = 'src="teacher-workflow.js"'
OUTCOME_MARKER = "mbm-outcome-id-safety:v1"
UNIT_DELETE_MARKER = "mbm-unit-delete-safety:v1"

DATA_MANAGER_ITEM = {
    "f": "Data_Manager_Studio.html",
    "n": "Data Manager Studio",
    "d": "Cohorts, stable learner IDs, qualification criteria, evidence coverage, review queues and secure-location backups — all local to this device",
    "i": "🧭",
    "c": "#2F6B4D",
    "new": True,
}


class UpgradeError(RuntimeError):
    pass


@dataclass(frozen=True)
class Change:
    path: Path
    before: bytes | None
    after: bytes
    reason: str

    @property
    def is_new(self) -> bool:
        return self.before is None

    @property
    def changed(self) -> bool:
        return self.before != self.after


def sha1_bytes(data: bytes) -> str:
    """Return the Git blob object ID used by GitHub for file contents."""
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def read_bytes(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


def decode(data: bytes, rel: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UpgradeError(f"{rel} is not valid UTF-8: {exc}") from exc


def ensure_repo(root: Path, strict_baseline: bool) -> list[str]:
    missing = [name for name in REQUIRED_REPO_FILES if not (root / name).is_file()]
    if missing:
        raise UpgradeError(
            "This does not look like the expected Matt-s-Apps- checkout. Missing: "
            + ", ".join(missing)
        )
    warnings: list[str] = []
    for rel, expected in BASELINE_SHA1.items():
        p = root / rel
        if not p.exists():
            continue
        actual = sha1_bytes(p.read_bytes())
        if actual != expected:
            msg = f"{rel}: source SHA-1 is {actual}, audited baseline was {expected}"
            if strict_baseline:
                raise UpgradeError(msg + " (strict baseline mode refuses to continue)")
            warnings.append(msg)
    return warnings


def inject_workflow(html: str, rel: str) -> str:
    head_count = html.count(WORKFLOW_HEAD_MARKER)
    script_count = html.count(WORKFLOW_SCRIPT_MARKER)
    if head_count > 1 or script_count > 1:
        raise UpgradeError(f"{rel}: duplicate teacher-workflow integration markers")
    if head_count == 0:
        if "</head>" not in html:
            raise UpgradeError(f"{rel}: cannot find </head> for additive stylesheet link")
        block = (
            f"\n{WORKFLOW_HEAD_MARKER}\n"
            '<link rel="stylesheet" href="teacher-workflow.css">\n'
        )
        html = html.replace("</head>", block + "</head>", 1)
    if script_count == 0:
        script = '<script defer src="teacher-workflow.js"></script>'
        hud = re.search(r'<script\s+defer\s+src="/hud\.js"\s*></script>', html)
        if hud:
            html = html[: hud.start()] + script + html[hud.start() :]
        elif "</body>" in html:
            html = html.replace("</body>", script + "</body>", 1)
        else:
            raise UpgradeError(f"{rel}: cannot find a safe script insertion point")
    if html.count(WORKFLOW_HEAD_MARKER) != 1 or html.count(WORKFLOW_SCRIPT_MARKER) != 1:
        raise UpgradeError(f"{rel}: integration marker cardinality is not exactly one")
    return html


def patch_evidence_binder(html: str) -> str:
    """Add two narrowly scoped data-integrity guards to the audited v1 binder."""
    if OUTCOME_MARKER not in html:
        pattern = re.compile(
            r"(?P<indent>[ \t]*)/\* keep outcome ids stable where text order matches, so existing tags survive edits \*/\s*"
            r"var old=u\.outcomes;\s*"
            r"u\.outcomes=lines\.map\(function\(txt,i\)\{\s*"
            r"return \{id:\(old\[i\]\?old\[i\]\.id:uid\(\)\),text:txt\};\s*"
            r"\}\);",
            re.MULTILINE,
        )
        match = pattern.search(html)
        if not match:
            raise UpgradeError(
                "Evidence_Binder.html: audited outcome-save anchor was not found. "
                "Refusing to guess around changed evidence logic."
            )
        i = match.group("indent")
        replacement = f"""{i}/* {OUTCOME_MARKER}
{i}   Exact wording matches preserve IDs across reordering. A same-position fallback
{i}   permits a deliberate wording edit. Linked criteria may not disappear silently. */
{i}var old=u.outcomes||[],byText={{}},used={{}},duplicate={{}};
{i}old.forEach(function(o){{
{i} var k=String(o.text||\"\").trim().toLowerCase();
{i} if(k&&!byText[k])byText[k]=o;
{i}}});
{i}lines.forEach(function(txt){{var k=txt.toLowerCase();duplicate[k]=(duplicate[k]||0)+1;}});
{i}if(Object.keys(duplicate).some(function(k){{return duplicate[k]>1;}})){{
{i} toast(\"Each outcome line must be unique before it can be saved\");return;
{i}}}
{i}var next=lines.map(function(txt,idx){{
{i} var k=txt.toLowerCase(),hit=byText[k];
{i} if(hit&&!used[hit.id]){{used[hit.id]=1;return {{id:hit.id,text:txt}};}}
{i} var positional=old[idx];
{i} if(positional&&!used[positional.id]){{used[positional.id]=1;return {{id:positional.id,text:txt}};}}
{i} return {{id:uid(),text:txt}};
{i}}});
{i}var linked={{}};
{i}ITEMS.forEach(function(it){{if(it.unitId===u.id)(it.outcomeIds||[]).forEach(function(id){{linked[id]=1;}});}});
{i}var removedLinked=old.filter(function(o){{
{i} return linked[o.id]&&!next.some(function(n){{return n.id===o.id;}});
{i}}});
{i}if(removedLinked.length){{
{i} toast(\"An outcome linked to evidence cannot be removed here. Keep it, or migrate the evidence first.\");return;
{i}}}
{i}u.outcomes=next;"""
        html = html[: match.start()] + replacement + html[match.end() :]

    if UNIT_DELETE_MARKER not in html:
        old = (
            ' var n=ITEMS.filter(function(it){return it.unitId===u.id;}).length;\n'
            ' if(!confirm("Delete \\u201c"+u.name+"\\u201d? "+(n?n+" evidence items stay stored but lose their unit tags.":"")))return;\n'
            ' META.units.splice(META.units.indexOf(u),1);'
        )
        if old not in html:
            # Accept source forms where the smart quotes have already been decoded.
            old_decoded = (
                ' var n=ITEMS.filter(function(it){return it.unitId===u.id;}).length;\n'
                ' if(!confirm("Delete “"+u.name+"”? "+(n?n+" evidence items stay stored but lose their unit tags.":"")))return;\n'
                ' META.units.splice(META.units.indexOf(u),1);'
            )
            if old_decoded in html:
                old = old_decoded
            else:
                raise UpgradeError(
                    "Evidence_Binder.html: audited unit-delete anchor was not found. "
                    "Refusing to alter unfamiliar deletion behaviour."
                )
        new = (
            f' /* {UNIT_DELETE_MARKER} */\n'
            ' var n=ITEMS.filter(function(it){return it.unitId===u.id;}).length;\n'
            ' if(n){toast("This unit has "+n+" linked evidence item"+(n===1?"":"s")+". It cannot be deleted; move or archive the evidence first.");return;}\n'
            ' if(!confirm("Delete this empty unit?"))return;\n'
            ' META.units.splice(META.units.indexOf(u),1);'
        )
        html = html.replace(old, new, 1)

    if html.count(OUTCOME_MARKER) != 1 or html.count(UNIT_DELETE_MARKER) != 1:
        raise UpgradeError("Evidence_Binder.html: safety marker cardinality is not exactly one")
    return html


def patch_apps_json(text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise UpgradeError(f"apps.json is invalid JSON: {exc}") from exc
    spaces = data.get("spaces")
    if not isinstance(spaces, list):
        raise UpgradeError("apps.json: spaces must be a list")
    teacher = next((s for s in spaces if s.get("cat") == "Teacher tools"), None)
    if not teacher or not isinstance(teacher.get("items"), list):
        raise UpgradeError("apps.json: Teacher tools catalogue section was not found")
    all_items = [it for space in spaces for it in space.get("items", [])]
    same_name = [it for it in all_items if it.get("n") == DATA_MANAGER_ITEM["n"]]
    if len(same_name) > 1:
        raise UpgradeError("apps.json: duplicate Data Manager Studio entries already exist")
    if same_name:
        same_name[0].update(DATA_MANAGER_ITEM)
        # Move the existing entry to the top of Teacher tools without deleting it.
        for space in spaces:
            if same_name[0] in space.get("items", []):
                space["items"].remove(same_name[0])
                break
        teacher["items"].insert(0, same_name[0])
    else:
        teacher["items"].insert(0, dict(DATA_MANAGER_ITEM))
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def patch_index(text: str) -> str:
    # Do not retain a manually maintained count in metadata.
    text = re.sub(r"\bwith\s+28\s+single-file studios\b", "with catalogue-driven single-file studios", text, count=1)
    text = text.replace("28 single-file studios", "single-file studios", 1)
    if '"Data Manager Studio":"t"' not in text:
        anchor = 'const AUDMAP={'
        if anchor not in text:
            raise UpgradeError("index.html: AUDMAP anchor was not found")
        text = text.replace(anchor, anchor + '"Data Manager Studio":"t",', 1)
    if text.count('"Data Manager Studio":"t"') != 1:
        raise UpgradeError("index.html: Data Manager audience mapping is duplicated")
    return text


def patch_readme(text: str) -> str:
    text = re.sub(
        r"A collection of \*\*23 self-contained, offline, single-file web tools\*\* for the classroom\.",
        "A catalogue of **self-contained, offline-first classroom tools**. The live total is derived from `apps.json` so the documentation cannot drift from the hub.",
        text,
        count=1,
    )
    text = text.replace("**`index.html`** (or **`Suite_Hub.html`**)", "**`index.html`**", 1)
    row = "| **Data Manager Studio** | Manage cohorts and stable learner IDs, map exact current unit criteria, collect evidence metadata and attachments, view gaps, prepare review queues, and export local backups or CSV reports. It never certifies achievement or uploads data automatically. |\n"
    if "| **Data Manager Studio** |" not in text:
        heading = "### Teacher tools\n| Tool | What it does |\n|---|---|\n"
        if heading not in text:
            raise UpgradeError("README.md: Teacher tools table anchor was not found")
        text = text.replace(heading, heading + row, 1)
    guard = (
        "\n### Evidence and awarding-body boundary\n"
        "- Built-in framework profiles are editable workflow templates, not specifications and not a substitute for the centre's current official documents.\n"
        "- An evidence count is not an assessment decision. Staff must review authenticity, sufficiency, independence/support and current criterion wording.\n"
        "- Data Manager backups contain personal data and attachments and are **not encrypted by the app**; store them only in an approved secure location.\n"
    )
    if "### Evidence and awarding-body boundary" not in text:
        privacy = "## 🔒 Privacy & safety\n"
        if privacy not in text:
            raise UpgradeError("README.md: privacy heading anchor was not found")
        text = text.replace(privacy, guard + "\n" + privacy, 1)
    return text


def collect_changes(root: Path) -> list[Change]:
    changes: list[Change] = []

    for rel in COPY_FILES:
        source = PROPOSED / rel
        if not source.is_file():
            raise UpgradeError(f"Upgrade pack is incomplete: proposed/{rel} is missing")
        after = source.read_bytes()
        target = root / rel
        before = read_bytes(target)
        if before is not None and before != after:
            # Upgrade-owned files can be refreshed only when they carry an expected identity marker.
            existing = decode(before, rel)
            identities = {
                "Data_Manager_Studio.html": "Data Manager Studio — Made by Matt",
                "teacher-workflow.js": "mbm.teacher.v1.context",
                "teacher-workflow.css": ".mbm-teacher-launcher",
                "evidence-schema-v2.json": "Made by Matt teacher evidence interchange record",
                "awarding-body-templates.json": "made-by-matt-awarding-body-workflow-templates",
            }
            if identities[rel] not in existing:
                raise UpgradeError(
                    f"{rel} already exists but is not recognisably upgrade-owned. Refusing to overwrite it."
                )
        changes.append(Change(target, before, after, "add or refresh upgrade-owned file"))

    for rel in WORKFLOW_TARGETS:
        path = root / rel
        before = path.read_bytes()
        text = decode(before, rel)
        if rel == "Evidence_Binder.html":
            text = patch_evidence_binder(text)
        text = inject_workflow(text, rel)
        changes.append(Change(path, before, text.encode("utf-8"), "add shared teacher workflow"))

    transforms: list[tuple[str, Callable[[str], str], str]] = [
        ("apps.json", patch_apps_json, "catalogue Data Manager Studio"),
        ("index.html", patch_index, "remove stale count and classify Data Manager"),
        ("README.md", patch_readme, "document local evidence workflow and guardrails"),
    ]
    for rel, fn, reason in transforms:
        path = root / rel
        before = path.read_bytes()
        after = fn(decode(before, rel)).encode("utf-8")
        changes.append(Change(path, before, after, reason))

    health_target = root / "suite-health.html"
    before = health_target.read_bytes()
    health = (PROPOSED / "suite-health-v2.html").read_bytes()
    existing_health = decode(before, "suite-health.html")
    if before != health and "Suite Health" not in existing_health:
        raise UpgradeError("suite-health.html is unfamiliar; refusing whole-file replacement")
    changes.append(Change(health_target, before, health, "replace stale inline-catalogue checker with catalogue-driven v2"))

    # One change per path, and no deletion operations can be represented by this model.
    seen: set[Path] = set()
    for change in changes:
        if change.path in seen:
            raise UpgradeError(f"Internal error: duplicate planned path {change.path}")
        seen.add(change.path)
    return [c for c in changes if c.changed]


def unified_diff(root: Path, changes: Iterable[Change]) -> str:
    pieces: list[str] = []
    for c in changes:
        rel = c.path.relative_to(root).as_posix()
        before = "" if c.before is None else c.before.decode("utf-8", errors="replace")
        after = c.after.decode("utf-8", errors="replace")
        pieces.extend(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=("/dev/null" if c.before is None else f"a/{rel}"),
                tofile=f"b/{rel}",
            )
        )
    return "".join(pieces)


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def apply_changes(root: Path, changes: list[Change]) -> Path | None:
    existing = [c for c in changes if c.before is not None]
    backup_root: Path | None = None
    if existing:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_root = root.parent / f"{root.name}-teacher-upgrade-backup-{stamp}"
        if backup_root.exists():
            raise UpgradeError(f"Backup destination already exists: {backup_root}")
        for c in existing:
            rel = c.path.relative_to(root)
            dest = backup_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(c.path, dest)
    for c in changes:
        atomic_write(c.path, c.after)
    return backup_root


def summary_payload(root: Path, changes: list[Change], warnings: list[str], backup: Path | None = None) -> dict:
    return {
        "repository": str(root),
        "auditedBaselineHead": BASELINE_HEAD,
        "changedFileCount": len(changes),
        "added": [str(c.path.relative_to(root)) for c in changes if c.is_new],
        "modified": [str(c.path.relative_to(root)) for c in changes if not c.is_new],
        "deleted": [],
        "warnings": warnings,
        "backup": str(backup) if backup else None,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", nargs="?", default=".", help="path to a Matt-s-Apps- checkout")
    p.add_argument("--apply", action="store_true", help="write files after backing up changed originals")
    p.add_argument("--emit-diff", metavar="PATH", help="write the exact planned unified diff")
    p.add_argument("--strict-baseline", action="store_true", help="require audited Git blob SHA-1 values")
    p.add_argument("--json", action="store_true", help="print machine-readable result JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.repo).expanduser().resolve()
    try:
        warnings = ensure_repo(root, args.strict_baseline)
        changes = collect_changes(root)
        diff = unified_diff(root, changes)
        if args.emit_diff:
            out = Path(args.emit_diff).expanduser().resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(diff, encoding="utf-8")
        backup = apply_changes(root, changes) if args.apply and changes else None
        payload = summary_payload(root, changes, warnings, backup)
        payload["mode"] = "applied" if args.apply else "dry-run"
        payload["diffPath"] = str(Path(args.emit_diff).expanduser().resolve()) if args.emit_diff else None
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Teacher upgrade {payload['mode']}: {len(changes)} file(s) would change." if not args.apply else f"Teacher upgrade applied: {len(changes)} file(s) changed.")
            for c in changes:
                kind = "ADD" if c.is_new else "MODIFY"
                print(f"  {kind:6} {c.path.relative_to(root)} — {c.reason}")
            print("  DELETE  none")
            if warnings:
                print("Warnings:")
                for warning in warnings:
                    print("  - " + warning)
            if backup:
                print(f"Backup: {backup}")
            if not changes:
                print("The checkout is already at this upgrade state.")
        return 0
    except UpgradeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
