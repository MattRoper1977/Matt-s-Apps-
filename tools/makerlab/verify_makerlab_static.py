#!/usr/bin/env python3
"""Static verifier for Teesside_Maker_Lab_PRO/. Usage: verify_makerlab_static.py <apps_repo_root> [--self-test]
Exit 1 on any failure. --self-test plants a window.open in a scratch copy and requires the verifier to go red."""
import sys, re, json, hashlib, pathlib, tempfile, shutil
ROOT = pathlib.Path(sys.argv[1]).resolve(); D = ROOT/'Teesside_Maker_Lab_PRO'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(d):
    fails=[]
    htmls=sorted(d.glob('*.html'))
    if len(htmls)!=15: fails.append(f'html count {len(htmls)} != 15')
    for h in htmls:
        t=h.read_text(encoding='utf-8',errors='replace')
        if 'window.open' in t: fails.append(f'{h.name}: window.open')
        if re.search(r"https?://(?!www\.w3\.org/(2000/svg|1999/xhtml))",t): fails.append(f'{h.name}: network URL')
        if re.search(r'\b(fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon)\s*\(',t): fails.append(f'{h.name}: network API')
        if 'prefers-reduced-motion' not in t: fails.append(f'{h.name}: no reduced-motion')
        ids=re.findall(r'\sid="([^"]+)"',t); dup={i for i in ids if ids.count(i)>1}
        if dup: fails.append(f'{h.name}: duplicate ids {sorted(dup)[:5]}')
        if 'lang="en-GB"' not in t and "lang='en-GB'" not in t: fails.append(f'{h.name}: lang')
    sh=(d/'STUDIO_SHELL.html').read_text(encoding='utf-8')
    if 'sandbox="allow-same-origin allow-scripts' not in sh: fails.append('M1 allow-same-origin missing')
    if 'e.source!==fr.contentWindow' not in sh: fails.append('M2 source guard missing')
    if (d/'VERSION.txt').read_text().strip()!='2.1.0': fails.append('VERSION.txt != 2.1.0')
    sums=(d/'SHA256SUMS.txt').read_text().splitlines()
    for l in sums:
        if not l.strip(): continue
        h,n=l.split(maxsplit=1)
        if not (d/n).exists(): fails.append(f'SHA256SUMS missing {n}')
        elif sha(d/n)!=h: fails.append(f'SHA256SUMS mismatch {n}')
    return fails
def main():
    fails=run(D)
    if '--self-test' in sys.argv:
        with tempfile.TemporaryDirectory() as td:
            tmp=pathlib.Path(td)/'Teesside_Maker_Lab_PRO'; shutil.copytree(D,tmp)
            f=tmp/'index.html'; f.write_text(f.read_text()+'<script>window.open("x")</script>')
            ctl=run(tmp)
            if not any('window.open' in x for x in ctl): fails.append('SELF-TEST: planted window.open not detected')
            else: print('[self-test] positive control fired OK')
    print(json.dumps({'status':'FAIL' if fails else 'PASS','failures':fails},indent=2))
    return 1 if fails else 0
if __name__=='__main__': raise SystemExit(main())
