#!/usr/bin/env python3
"""Re-pin the estate's source manifests after a deliberate change to one.

WHAT IS PINNED, AND WHY BY DIGEST
---------------------------------
Two manifests drive the estate's derived UI and used to sit under a blanket
"must not change" rule that forbade the repositories' ordinary business:

  apps.json        (Matt-s-Apps-)   the studio catalogue — pinned under Ruling 1
  resources.json   (Lessons)        the lesson catalogue — pinned under Ruling 3

Each is guarded by a SHA-256 pin inside verify_cross_estate_unification.py
rather than by prohibition: a deliberate change re-pins in the same commit,
where a reviewer sees the moved digest; an edit that does not re-pin goes red
on every gate run, not only when git happens to show a diff.

THE NAME
--------
This tool started life as pin_apps_manifest.py, which was true for exactly as
long as it pinned one manifest. Ruling 3 added resources.json and ruled that
the name must stop lying about its scope — hence pin_manifests.py. The old
name is gone; ALLOWED_DIFF retains the old entry so the rename's deletion
stays legal in any historical diff span.

BOTH GATE COPIES, ONE RUN
-------------------------
verify_cross_estate_unification.py is byte-identical in Lessons and Apps, and
both pins live inside it. This tool writes both copies or neither — checked
BEFORE the first write, because an earlier version checked as it went and left
one copy rewritten when it failed on the second, which is precisely the
divergence a shared file must never be left in.

    python3 tools/pin_manifests.py            re-pin from the current manifests
    python3 tools/pin_manifests.py --check    report drift, write nothing, exit 1
    python3 tools/pin_manifests.py --self-test
    python3 tools/pin_manifests.py --apps DIR --lessons DIR   explicit roots
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
GATE_REL = "tools/verify_cross_estate_unification.py"


def _first(*c: Path) -> Path | None:
    for p in c:
        if p is not None and p.exists():
            return p
    return None


def detect_roots() -> tuple[Path | None, Path | None]:
    """(apps_root, lessons_root), from wherever this copy of the tool lives."""
    if (HERE / "apps.json").is_file():
        apps = HERE
        lessons = _first(HERE.parent / "Lessons", Path("/home/user/Lessons"))
    elif (HERE / "resources.json").is_file():
        lessons = HERE
        apps = _first(HERE.parent / "matt-s-apps-", Path("/workspace/matt-s-apps-"))
    else:
        apps = _first(Path("/workspace/matt-s-apps-"))
        lessons = _first(Path("/home/user/Lessons"))
    return apps, lessons


APPS, LESSONS = detect_roots()

# manifest name -> (owning root, pin regex inside the gate). Anchored on the
# manifest's own name so neither can match the other's pin.
def manifests() -> dict[str, tuple[Path | None, re.Pattern]]:
    return {
        "apps.json": (APPS, re.compile(r'("apps\.json":\s*")([0-9a-f]{64})(")')),
        "resources.json": (LESSONS, re.compile(r'("resources\.json":\s*")([0-9a-f]{64})(")')),
    }


def gates() -> list[Path]:
    out = []
    for root in (APPS, LESSONS):
        if root and (root / GATE_REL).is_file():
            out.append(root / GATE_REL)
    return out


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def preflight(targets: list[Path]) -> str | None:
    """Every gate copy must carry a movable pin for every manifest, BEFORE any
    write. Writing one of two copies is how the shared file diverges."""
    if len(targets) < 2:
        return ("only one copy of the gate is reachable — re-pinning one of two leaves "
                "the repositories disagreeing. Check out both, or pass --apps/--lessons.")
    for g in targets:
        text = g.read_text(encoding="utf-8")
        for name, (_root, rx) in manifests().items():
            if not rx.search(text):
                return (f"{g} carries no {name} pin to move — an older copy of the gate. "
                        f"Bring both copies to the same version first.")
    return None


def run(write: bool) -> int:
    targets = gates()
    wanted: dict[str, str] = {}
    print("manifests:")
    for name, (root, _rx) in manifests().items():
        if root is None or not (root / name).is_file():
            print(f"   MISSING {name} (no owning checkout found)")
            return 1
        wanted[name] = digest(root / name)
        print(f"   {name:16} {root / name}")
        print(f"   {'':16} sha256 {wanted[name]}")
    print(f"gate copies {len(targets)}: {', '.join(str(t) for t in targets)}\n")

    hole = preflight(targets)
    if hole:
        print(f"   HOLE    {hole}\n\n[FAIL] nothing written — see above")
        return 1

    stale = []
    for g in targets:
        text = g.read_text(encoding="utf-8")
        moved = []
        for name, (_root, rx) in manifests().items():
            m = rx.search(text)
            if m.group(2) != wanted[name]:
                moved.append((name, m.group(2)[:12], wanted[name][:12]))
                text = rx.sub(lambda mm, w=wanted[name]: mm.group(1) + w + mm.group(3), text, count=1)
        if not moved:
            print(f"   ok      {g}")
            continue
        stale.append(g)
        if write:
            g.write_text(text, encoding="utf-8")
            for name, old, new in moved:
                print(f"   REPINNED {g}   {name}: {old} -> {new}")
        else:
            for name, old, new in moved:
                print(f"   STALE   {g}   {name}: pinned {old}, manifest is {new}")

    print()
    if not stale:
        print("[PASS] every manifest matches its pin in every copy of the gate")
        return 0
    if write:
        if len({g.read_bytes() for g in targets}) != 1:
            print("[FAIL] the gate copies are NOT byte-identical after re-pinning — they "
                  "differed for some other reason too; fix that before relying on the pins")
            return 1
        print(f"[DONE] pins moved in {len(stale)} copy/copies; both copies byte-identical")
        return 0
    print("[FAIL] a manifest does not match its pin. If you changed it on purpose:\n"
          "           python3 tools/pin_manifests.py")
    return 1


def self_test() -> int:
    """Each manifest's drift must redden --check, and the tree must come back."""
    problems = []
    for name, (root, _rx) in manifests().items():
        if root is None:
            problems.append(f"{name}: no owning checkout to test against")
            continue
        p = root / name
        original = p.read_bytes()
        try:
            p.write_bytes(original + b"\n")
            if digest(p) == hashlib.sha256(original).hexdigest():
                problems.append(f"{name}: THE SABOTAGE DID NOT LAND")
            elif run(write=False) == 0:
                problems.append(f"{name}: --check accepted a manifest that no longer matches its pin")
        finally:
            p.write_bytes(original)
        if p.read_bytes() != original:
            problems.append(f"{name}: RESTORE FAILED")
    if run(write=False) != 0:
        problems.append("after restoring, --check still reports drift")
    for x in problems:
        print("   FAIL " + x)
    if problems:
        print(f"[FAIL] pin self-test: {len(problems)} problem(s)")
        return 1
    print("[PASS] pin self-test: drifting either manifest reddens --check, both restores "
          "verified, and a clean tree passes")
    return 0


def main() -> int:
    global APPS, LESSONS
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apps", help="path to the Matt-s-Apps- checkout")
    ap.add_argument("--lessons", help="path to the Lessons checkout")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.apps:
        APPS = Path(a.apps).resolve()
    if a.lessons:
        LESSONS = Path(a.lessons).resolve()
    if a.self_test:
        return self_test()
    return run(write=not a.check)


if __name__ == "__main__":
    raise SystemExit(main())
