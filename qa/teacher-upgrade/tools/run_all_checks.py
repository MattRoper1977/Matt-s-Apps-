#!/usr/bin/env python3
"""Run upgrade-pack contract and syntax checks; optionally run Chromium smoke."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, cmd: list[str]) -> dict:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    result = {"label": label, "status": "pass" if p.returncode == 0 else "fail", "command": cmd, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    print(f"{result['status'].upper():4} {label}")
    if p.returncode:
        print(p.stdout)
        print(p.stderr, file=sys.stderr)
    return result


def node_check_inline(path: Path) -> list[dict]:
    html = path.read_text(encoding="utf-8")
    scripts = [m.group(1) for m in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.I | re.S)]
    out=[]
    for i, script in enumerate(scripts,1):
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
            f.write(script); tmp=Path(f.name)
        try: out.append(run(f"Node syntax {path.name} inline #{i}",["node","--check",str(tmp)]))
        finally: tmp.unlink(missing_ok=True)
    return out


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--browser", action="store_true")
    ap.add_argument("--browser-executable", default="")
    args=ap.parse_args()
    py=sys.executable
    results=[]
    for path in sorted((ROOT/"tools").glob("*.py"))+sorted((ROOT/"tests").glob("*.py")):
        results.append(run(f"Python compile {path.relative_to(ROOT)}",[py,"-m","py_compile",str(path)]))
    for path in sorted(ROOT.rglob("*.json")):
        if path == ROOT/"reports/PACK_CHECK_RESULTS.json":
            continue
        try:
            json.loads(path.read_text(encoding="utf-8")); results.append({"label":f"JSON parse {path.relative_to(ROOT)}","status":"pass","command":[],"stdout":"","stderr":""}); print(f"PASS JSON parse {path.relative_to(ROOT)}")
        except Exception as exc:
            results.append({"label":f"JSON parse {path.relative_to(ROOT)}","status":"fail","command":[],"stdout":"","stderr":str(exc)}); print(f"FAIL JSON parse {path.relative_to(ROOT)}")
    results.append(run("Node syntax teacher-workflow.js",["node","--check",str(ROOT/"proposed/teacher-workflow.js")]))
    results.extend(node_check_inline(ROOT/"proposed/Data_Manager_Studio.html"))
    results.extend(node_check_inline(ROOT/"proposed/suite-health-v2.html"))
    results.append(run("Patcher contract",[py,str(ROOT/"tools/test_apply_teacher_upgrade.py")]))
    results.append(run("Verifier positive/negative controls",[py,str(ROOT/"tools/test_verify_teacher_upgrade.py")]))
    if args.browser:
        cmd=[py,str(ROOT/"tests/browser_smoke.py")]
        if args.browser_executable: cmd += ["--browser-executable",args.browser_executable]
        results.append(run("Chromium browser smoke",cmd))
    summary={"pass":sum(1 for r in results if r["status"]=="pass"),"fail":sum(1 for r in results if r["status"]=="fail")}
    (ROOT/"reports/PACK_CHECK_RESULTS.json").write_text(json.dumps({"summary":summary,"results":results},indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))
    return 1 if summary["fail"] else 0

if __name__=="__main__": raise SystemExit(main())
