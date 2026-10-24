#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_apply_teacher_upgrade import write_fixture  # noqa: E402
from verify_teacher_upgrade import BASELINE_FILES  # noqa: E402

PATCHER = HERE / "apply_teacher_upgrade.py"
VERIFIER = HERE / "verify_teacher_upgrade.py"


def run(cmd: list[str], ok: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(cmd, text=True, capture_output=True)
    if ok and p.returncode != 0:
        raise AssertionError(f"failed: {' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
    if not ok and p.returncode == 0:
        raise AssertionError(f"unexpected success: {' '.join(cmd)}")
    return p


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mbm-verify-test-") as td:
        repo = Path(td) / "Matt-s-Apps-"
        write_fixture(repo)
        for rel in BASELINE_FILES:
            p = repo / rel
            if p.exists():
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.suffix == ".html":
                p.write_text(f"<!doctype html><html><head><title>{rel}</title></head><body></body></html>", encoding="utf-8")
            elif p.suffix == ".svg":
                p.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
            else:
                p.write_bytes(b"fixture")
        run([sys.executable, str(PATCHER), str(repo), "--apply", "--json"])
        result = run([sys.executable, str(VERIFIER), str(repo), "--json"])
        payload = json.loads(result.stdout)
        assert payload["summary"]["fail"] == 0, payload
        assert payload["summary"]["pass"] >= 30, payload

        # Positive controls: each deliberately broken contract must fail.
        (repo / "Feelings_Checkin.html").write_text('<script src="teacher-workflow.js"></script>', encoding="utf-8")
        bad = run([sys.executable, str(VERIFIER), str(repo), "--json"], ok=False)
        bad_payload = json.loads(bad.stdout)
        assert any(f["status"] == "fail" and "privacy exclusion" in f["check"] for f in bad_payload["findings"])

    print("PASS: verifier accepts a valid synthetic upgrade and rejects a privacy-boundary violation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
