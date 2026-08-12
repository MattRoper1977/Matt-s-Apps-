#!/usr/bin/env python3
"""Re-pin apps.json after a deliberate change to it.

WHY A PIN AND NOT AN ALLOWANCE
------------------------------
verify_cross_estate_unification.py used to say "apps.json must not change".
That is a clean rule with one problem: adding a studio IS an apps.json change,
so the rule forbade the ordinary business of this repository. It also touches
index.html (AUDMAP + the no-JS lead count), which is in the workflow's path
filter, so the gate fired every time and refused.

The obvious fix — put apps.json in ALLOWED_DIFF and move on — retires the
protection entirely, and does it quietly. Nobody would notice the manifest was
no longer guarded until something rewrote it.

So apps.json is pinned instead, the way tools/sync_theme.py pins the generated
theme copies. The digest lives in the gate; this tool moves it. A deliberate
change re-pins in the same commit, and the moved pin shows up in the diff where
a reviewer sees it. An edit that does not re-pin goes red.

BOTH COPIES, ONE RUN
--------------------
verify_cross_estate_unification.py is kept byte-identical in Lessons and Apps.
The pin lives inside it, so re-pinning one copy and not the other would reopen
exactly the divergence this estate has already had to close once. This tool
writes both, or writes neither and says why — checked BEFORE the first write,
because a version that checked as it went left one copy rewritten and the other
not when it hit a problem halfway.

    python3 tools/pin_apps_manifest.py            re-pin from the current apps.json
    python3 tools/pin_apps_manifest.py --check    report drift, write nothing, exit 1
    python3 tools/pin_apps_manifest.py --self-test
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

APPS = Path(__file__).resolve().parent.parent
MANIFEST = APPS / "apps.json"
GATE_REL = "tools/verify_cross_estate_unification.py"

PIN_RX = re.compile(r'("apps\.json":\s*")([0-9a-f]{64})(")')


def _first(*c: Path) -> Path | None:
    for p in c:
        if p.exists():
            return p
    return None


LESSONS = _first(APPS.parent / "Lessons", Path("/home/user/Lessons"))


def gates() -> list[Path]:
    out = [APPS / GATE_REL]
    if LESSONS and (LESSONS / GATE_REL).is_file():
        out.append(LESSONS / GATE_REL)
    return out


def preflight(targets: list[Path]) -> str | None:
    """Every copy must carry a movable pin BEFORE any copy is written."""
    for g in targets:
        if not g.is_file():
            return f"{g} does not exist"
        if not PIN_RX.search(g.read_text(encoding="utf-8")):
            return (f"{g} carries no apps.json pin to move — it is an older copy of the "
                    f"gate. Bring both copies to the same version first; re-pinning one "
                    f"of two is how the copies drift apart.")
    return None


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(write: bool) -> int:
    if not MANIFEST.is_file():
        print(f"[FAIL] no apps.json at {MANIFEST}")
        return 1
    want = digest(MANIFEST)
    targets = gates()
    print(f"apps.json  {MANIFEST}")
    print(f"           {MANIFEST.stat().st_size} B  sha256 {want}")
    print(f"gate copies {len(targets)}: {', '.join(str(t) for t in targets)}\n")

    if len(targets) < 2:
        print("[FAIL] only one copy of the gate is reachable. Re-pinning one and not the "
              "other leaves the two repositories disagreeing about the pin, which is the "
              "divergence this tool exists to prevent. Check out both and re-run, or pass "
              "--lessons <path>.")
        return 1
    hole = preflight(targets)
    if hole:
        print(f"   HOLE    {hole}\n\n[FAIL] nothing written — see above")
        return 1

    stale = []
    for g in targets:
        text = g.read_text(encoding="utf-8")
        m = PIN_RX.search(text)
        if m.group(2) == want:
            print(f"   ok      {g}")
            continue
        stale.append(g)
        if write:
            g.write_text(PIN_RX.sub(lambda mm: mm.group(1) + want + mm.group(3), text, count=1),
                         encoding="utf-8")
            print(f"   REPINNED {g}   {m.group(2)[:12]} -> {want[:12]}")
        else:
            print(f"   STALE   {g}   pinned {m.group(2)[:12]}, apps.json is {want[:12]}")

    print()
    if not stale:
        print("[PASS] apps.json matches its pin in every copy of the gate")
        return 0
    if write:
        if len({g.read_bytes() for g in targets}) != 1:
            print("[FAIL] the gate copies are NOT byte-identical after re-pinning — they "
                  "differed for some other reason too; fix that before relying on the pin")
            return 1
        print(f"[DONE] pin moved in {len(stale)} copy/copies; both copies byte-identical")
        return 0
    print("[FAIL] apps.json does not match its pin. If you changed it on purpose:\n"
          "           python3 tools/pin_apps_manifest.py")
    return 1


def self_test() -> int:
    """Prove --check reddens on a changed manifest, and that the tree is restored."""
    problems = []
    original = MANIFEST.read_bytes()
    try:
        MANIFEST.write_bytes(original + b"\n")
        if digest(MANIFEST) == hashlib.sha256(original).hexdigest():
            problems.append("THE SABOTAGE DID NOT LAND — apps.json unchanged")
        elif run(write=False) == 0:
            problems.append("--check accepted an apps.json that no longer matches its pin")
    finally:
        MANIFEST.write_bytes(original)
    if digest(MANIFEST) != hashlib.sha256(original).hexdigest():
        problems.append("RESTORE FAILED — apps.json left modified")
    if run(write=False) != 0:
        problems.append("after restoring, --check still reports drift")

    for p in problems:
        print("   FAIL " + p)
    if problems:
        print(f"[FAIL] pin self-test: {len(problems)} problem(s)")
        return 1
    print("[PASS] pin self-test: a changed apps.json reddens --check, the tree was restored, "
          "and a matching manifest passes")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--lessons", help="path to the Lessons checkout, when it is not beside this one")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.lessons:
        global LESSONS
        LESSONS = Path(a.lessons).resolve()
    if a.self_test:
        return self_test()
    return run(write=not a.check)


if __name__ == "__main__":
    raise SystemExit(main())
