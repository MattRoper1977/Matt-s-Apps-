#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATCHER = HERE / "apply_teacher_upgrade.py"
TARGETS = [
    "Evidence_Binder.html", "Classroom_Toolkit.html", "Seating_Studio.html",
    "Rubric_Studio.html", "Exit_Ticket.html", "Writing_Frames.html",
    "Quiz_Studio.html", "Graph_Studio.html", "Whiteboard.html", "PDF_Studio.html",
    "ChoreoStudio.html",
]


def html(title: str) -> str:
    return f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title></head><body><main>{title}</main><script defer src="/hud.js"></script></body></html>\n'


def evidence_html() -> str:
    return r'''<!doctype html><html><head><title>Evidence Binder</title></head><body>
<script>
var META={units:[]},ITEMS=[];function uid(){return "x";}function toast(){}function metaSave(){return Promise.resolve();}function renderSetup(){}function unitById(){return META.units[0];}function $(){return {value:""};}
function saveUnit(){
 var us=$("suUnit"),u=unitById(us.value);
 var name=($("suName").value||"").trim();
 if(!name){toast("Give the unit a name");return;}
 var lines=($("suOuts").value||"").split("\n").map(function(s){return s.trim();}).filter(Boolean);
 if(!lines.length){toast("Paste at least one outcome");return;}
 if(!u){u={id:uid(),outcomes:[]};META.units.push(u);}
 u.name=name;u.code=($("suCode").value||"").trim();
 /* keep outcome ids stable where text order matches, so existing tags survive edits */
 var old=u.outcomes;
 u.outcomes=lines.map(function(txt,i){
  return {id:(old[i]?old[i].id:uid()),text:txt};
 });
 metaSave().then(function(){toast("Unit saved ✓");renderSetup();});
}
function delUnit(){
 var u=unitById($("suUnit").value);
 if(!u)return;
 var n=ITEMS.filter(function(it){return it.unitId===u.id;}).length;
 if(!confirm("Delete \u201c"+u.name+"\u201d? "+(n?n+" evidence items stay stored but lose their unit tags.":"")))return;
 META.units.splice(META.units.indexOf(u),1);
 metaSave().then(function(){toast("Unit deleted");renderSetup();});
}
</script><script defer src="/hud.js"></script></body></html>
'''


def write_fixture(root: Path) -> None:
    root.mkdir()
    for name in TARGETS:
        (root / name).write_text(evidence_html() if name == "Evidence_Binder.html" else html(name), encoding="utf-8")
    apps = {
        "title": "Studio Suite",
        "spaces": [
            {"cat": "Teacher tools", "items": [{"f": "Evidence_Binder.html", "n": "Evidence Binder", "d": "x", "i": "📒", "c": "#b4892c"}]},
            {"cat": "Learn & organise", "items": [{"f": "Writing_Frames.html", "n": "Writing Frames Studio", "d": "x", "i": "✍️", "c": "#0d9488"}]},
        ],
    }
    (root / "apps.json").write_text(json.dumps(apps), encoding="utf-8")
    (root / "index.html").write_text(
        '<!doctype html><html><head><meta name="description" content="with 28 single-file studios"></head><body><script>const AUDMAP={"Evidence Binder":"t"};</script></body></html>',
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# Matt's Apps — Studio Suite\n\n"
        "A collection of **23 self-contained, offline, single-file web tools** for the classroom.\n\n"
        "Open **`index.html`** (or **`Suite_Hub.html`**).\n\n"
        "### Teacher tools\n| Tool | What it does |\n|---|---|\n| **Evidence Binder** | Evidence |\n\n"
        "## 🔒 Privacy & safety\n\nLocal.\n",
        encoding="utf-8",
    )
    (root / "suite-health.html").write_text("<!doctype html><title>Suite Health</title><script>const re=/f:\"([^\"]+)\"/g;</script>", encoding="utf-8")


def run(*args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run([sys.executable, str(PATCHER), *args], text=True, capture_output=True)
    if ok and p.returncode != 0:
        raise AssertionError(f"command failed ({p.returncode})\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")
    if not ok and p.returncode == 0:
        raise AssertionError("command unexpectedly succeeded")
    return p


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mbm-upgrade-test-") as td:
        base = Path(td)
        repo = base / "Matt-s-Apps-"
        write_fixture(repo)
        original = {p.name: p.read_bytes() for p in repo.iterdir() if p.is_file()}
        diff = base / "planned.patch"

        dry = run(str(repo), "--emit-diff", str(diff), "--json")
        payload = json.loads(dry.stdout)
        assert payload["mode"] == "dry-run"
        assert payload["deleted"] == []
        assert payload["changedFileCount"] == 20, payload
        assert diff.exists() and "Data_Manager_Studio.html" in diff.read_text(encoding="utf-8")
        assert {p.name: p.read_bytes() for p in repo.iterdir() if p.is_file()} == original, "dry-run wrote to checkout"

        applied = run(str(repo), "--apply", "--json")
        result = json.loads(applied.stdout)
        assert result["mode"] == "applied"
        assert result["deleted"] == []
        backup = Path(result["backup"])
        assert backup.is_dir()
        for name, data in original.items():
            assert (repo / name).exists(), f"source file deleted: {name}"
            if name in result["modified"]:
                assert (backup / name).read_bytes() == data, f"backup mismatch: {name}"

        for name in ["Data_Manager_Studio.html", "teacher-workflow.js", "teacher-workflow.css", "evidence-schema-v2.json", "awarding-body-templates.json"]:
            assert (repo / name).is_file(), name
        for name in TARGETS:
            text = (repo / name).read_text(encoding="utf-8")
            assert text.count("mbm-teacher-workflow:v1") == 1, name
            assert text.count('src="teacher-workflow.js"') == 1, name
        evidence = (repo / "Evidence_Binder.html").read_text(encoding="utf-8")
        assert evidence.count("mbm-outcome-id-safety:v1") == 1
        assert evidence.count("mbm-unit-delete-safety:v1") == 1
        assert "stay stored but lose their unit tags" not in evidence
        assert "cannot be deleted" in evidence

        catalogue = json.loads((repo / "apps.json").read_text(encoding="utf-8"))
        teacher = next(x for x in catalogue["spaces"] if x["cat"] == "Teacher tools")
        assert teacher["items"][0]["n"] == "Data Manager Studio"
        assert (repo / "index.html").read_text().count('"Data Manager Studio":"t"') == 1
        assert "28 single-file studios" not in (repo / "index.html").read_text()
        assert "Suite_Hub.html" not in (repo / "README.md").read_text()
        assert "Data Manager Studio" in (repo / "README.md").read_text()
        assert "apps.json" in (repo / "suite-health.html").read_text()

        second = run(str(repo), "--apply", "--json")
        result2 = json.loads(second.stdout)
        assert result2["changedFileCount"] == 0, result2
        assert result2["backup"] is None

        conflict = base / "conflict"
        shutil.copytree(repo, conflict)
        (conflict / "teacher-workflow.js").write_text("unrelated file", encoding="utf-8")
        bad = run(str(conflict), ok=False)
        assert "not recognisably upgrade-owned" in bad.stderr

    print("PASS: patcher dry-run, backup, no-delete, safety, conflict and idempotence contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
