#!/usr/bin/env python3
"""Static gate for the deployed LundyLoop Professional OS payload."""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, subprocess, sys, tempfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ENTRY = "LundyLoop_Professional_OS.html"
SUITE = "LundyLoop_Professional_OS"
MANIFEST = "_release-docs/lundyloop-professional-os-v2/PAYLOAD_MANIFEST.json"
EXPECTED_NAME = "LundyLoop Professional OS"
FORBIDDEN_BITS = ("full_backup", "redacted_audit", "capsule", "screenshot_errors", "import_qa", "crypto_unit", ".wav", ".webm", ".mp3")
NETWORK = {
    "fetch": re.compile(r"\bfetch\s*\("),
    "xhr": re.compile(r"\bXMLHttpRequest\b"),
    "websocket": re.compile(r"\bWebSocket\s*\("),
    "eventsource": re.compile(r"\bEventSource\s*\("),
}

def sha(p: Path) -> str:
    h=hashlib.sha256();
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.ids=[]; self.links=[]; self.runtime=[]; self.scripts=[]; self._in=False; self._parts=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if a.get("id"): self.ids.append(a["id"])
        if tag=="a" and a.get("href"): self.links.append(a["href"])
        if tag in {"script","img","iframe","audio","video","source"} and a.get("src"): self.runtime.append((tag,a["src"]))
        if tag=="link" and a.get("href"):
            rel={x.lower() for x in (a.get("rel") or "").split()}
            if rel & {"stylesheet","icon","preload","modulepreload","manifest"}: self.runtime.append((tag,a["href"]))
        if tag=="script" and not a.get("src"): self._in=True; self._parts=[]
    def handle_endtag(self, tag):
        if tag=="script" and self._in: self.scripts.append("".join(self._parts)); self._in=False; self._parts=[]
    def handle_data(self, data):
        if self._in: self._parts.append(data)

def external_runtime(u: str) -> bool:
    if u.startswith(("data:","blob:","#","/")): return False
    p=urlparse(u); return p.scheme in {"http","https"} or u.startswith("//")

def resolve(root: Path, page: Path, href: str):
    if href.startswith(("#","/","mailto:","tel:","data:","blob:","http://","https://","//")): return None
    clean=href.split("#",1)[0].split("?",1)[0]
    if not clean: return None
    p=(page.parent/clean).resolve()
    if clean.endswith("/"): p=p/"index.html"
    return p

def number_word(n:int)->str:
    one=["Zero","One","Two","Three","Four","Five","Six","Seven","Eight","Nine","Ten","Eleven","Twelve","Thirteen","Fourteen","Fifteen","Sixteen","Seventeen","Eighteen","Nineteen"]
    tens=["","","Twenty","Thirty","Forty","Fifty","Sixty","Seventy","Eighty","Ninety"]
    if 0<=n<20:return one[n]
    if 20<=n<100:return tens[n//10]+("-"+one[n%10].lower() if n%10 else "")
    return str(n)

def run(root: Path, *, require_catalogue: bool, node_check: bool=True):
    root=root.resolve(); fail=[]; warn=[]; metrics={"html":0,"inline_scripts":0,"links":0,"manifest_records":0}
    manifest_path=root/MANIFEST
    if not manifest_path.is_file(): fail.append(f"missing payload manifest: {MANIFEST}"); records=[]
    else:
        try: records=json.loads(manifest_path.read_text(encoding="utf-8"))["records"]
        except Exception as e: fail.append(f"invalid payload manifest: {e}"); records=[]
    metrics["manifest_records"]=len(records)
    for rec in records:
        p=root/rec["path"]
        if not p.is_file(): fail.append(f"manifest file missing: {rec['path']}"); continue
        if p.stat().st_size!=rec["bytes"]: fail.append(f"size mismatch: {rec['path']}")
        if sha(p)!=rec["sha256"]: fail.append(f"sha mismatch: {rec['path']}")
    for needed in [ENTRY, f"{SUITE}/index.html", f"{SUITE}/LundyLoop_PRO_Participation_Operating_System.html"]:
        if not (root/needed).is_file(): fail.append(f"missing required runtime: {needed}")
    for p in root.rglob("*"):
        if p.is_file() and any(x in p.relative_to(root).as_posix().lower() for x in FORBIDDEN_BITS): fail.append(f"forbidden production artefact: {p.relative_to(root)}")
    scripts=[]
    scan_roots=[root/ENTRY, *sorted((root/SUITE).rglob("*.html"))]
    for p in scan_roots:
        if not p.is_file(): continue
        metrics["html"]+=1; text=p.read_text(encoding="utf-8"); s=Scan(); s.feed(text)
        dup=[k for k,v in Counter(s.ids).items() if v>1]
        if dup: fail.append(f"duplicate ids in {p.relative_to(root)}: {dup}")
        for tag,u in s.runtime:
            if external_runtime(u): fail.append(f"external runtime asset in {p.relative_to(root)}: {tag} {u}")
        for name,rx in NETWORK.items():
            if rx.search(text): fail.append(f"network API {name} in {p.relative_to(root)}")
        for href in s.links:
            target=resolve(root,p,href)
            if target is None: continue
            metrics["links"]+=1
            try: target.relative_to(root)
            except ValueError: fail.append(f"link escapes Apps tree in {p.relative_to(root)}: {href}"); continue
            if not target.exists():
                if not require_catalogue and target == root / "index.html":
                    continue
                fail.append(f"broken internal link in {p.relative_to(root)}: {href}")
        for i,body in enumerate(s.scripts):
            if body.strip(): scripts.append((p.relative_to(root).as_posix(),i,body))
    metrics["inline_scripts"]=len(scripts)
    entry_text=(root/ENTRY).read_text(encoding="utf-8") if (root/ENTRY).is_file() else ""
    for token in ['href="./"','href="LundyLoop_Professional_OS/"','LundyLoop Pro']:
        if token not in entry_text: fail.append(f"root flagship deployment route missing: {token}")
    if node_check:
        try:
            subprocess.run(["node","--version"],check=True,capture_output=True,text=True)
            with tempfile.TemporaryDirectory(prefix="lundy-js-") as td:
                td=Path(td)
                for n,(rel,i,body) in enumerate(scripts):
                    f=td/f"{n}.js"; f.write_text(body,encoding="utf-8")
                    cp=subprocess.run(["node","--check",str(f)],capture_output=True,text=True)
                    if cp.returncode: fail.append(f"JavaScript syntax failure {rel} script {i}: {cp.stderr.strip()}")
        except FileNotFoundError: warn.append("node absent; JavaScript syntax check skipped")
    apps=root/"apps.json"; hub=root/"index.html"
    if require_catalogue:
        if not apps.is_file(): fail.append("apps.json missing")
        else:
            try:
                data=json.loads(apps.read_text(encoding="utf-8")); spaces=data["spaces"]
                hits=[(s,it) for s in spaces for it in s.get("items",[]) if it.get("n")==EXPECTED_NAME]
                if len(hits)!=1: fail.append(f"expected exactly one catalogue entry, found {len(hits)}")
                elif hits[0][0].get("cat")!="Teacher tools": fail.append("catalogue entry is not in Teacher tools")
                elif hits[0][1].get("f")!=ENTRY: fail.append(f"catalogue route is {hits[0][1].get('f')!r}, expected {ENTRY!r}")
                total=sum(len(s.get("items",[])) for s in spaces)
                if hub.is_file():
                    ht=hub.read_text(encoding="utf-8")
                    if f'"{EXPECTED_NAME}":"t"' not in ht: fail.append("Apps AUDMAP does not classify LundyLoop as Teacher Admin")
                    if f'<span id="leadCount">{number_word(total)}</span>' not in ht: fail.append("no-JS Apps count does not match apps.json")
                else: fail.append("Apps index.html missing")
            except Exception as e: fail.append(f"catalogue validation failed: {e}")
    return {"status":"PASS" if not fail else "FAIL","root":str(root),"metrics":metrics,"failures":fail,"warnings":warn}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("root",type=Path,nargs="?",default=Path(".")); ap.add_argument("--payload-only",action="store_true"); ap.add_argument("--json-out",type=Path); ap.add_argument("--skip-node",action="store_true"); ap.add_argument("--self-test",action="store_true"); a=ap.parse_args()
    result=run(a.root,require_catalogue=not a.payload_only,node_check=not a.skip_node)
    print(json.dumps(result,indent=2))
    if a.json_out: a.json_out.parent.mkdir(parents=True,exist_ok=True); a.json_out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    if result["failures"]: return 1
    if a.self_test:
        with tempfile.TemporaryDirectory(prefix="lundy-control-") as td:
            fixture=Path(td)/"repo"; shutil.copytree(a.root,fixture)
            victim=fixture/SUITE/"pupil_tools/02_LundyLoop_Tokenism_Detective.html"; victim.unlink()
            bad=run(fixture,require_catalogue=not a.payload_only,node_check=False)
            if not bad["failures"]:
                print("[FAIL] positive control did not detect a removed runtime file",file=sys.stderr); return 1
            print(f"[PASS] positive control detected {len(bad['failures'])} error(s)")
    return 0
if __name__=="__main__": raise SystemExit(main())
