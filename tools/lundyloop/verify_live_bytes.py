#!/usr/bin/env python3
"""Wait for and prove exact served LundyLoop payload bytes."""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,default=Path('.'));ap.add_argument('--base',required=True);ap.add_argument('--sha',required=True);ap.add_argument('--attempts',type=int,default=60);ap.add_argument('--sleep',type=float,default=10);ap.add_argument('--json-out',type=Path);a=ap.parse_args()
 root=a.repo_root.resolve();manifest=json.loads((root/'_release-docs/lundyloop-professional-os-v2/PAYLOAD_MANIFEST.json').read_text(encoding='utf-8'));records=[r for r in manifest['records'] if r['path'].endswith(('.html','.jpg'))]
 base=a.base if a.base.endswith('/') else a.base+'/';results=[];all_ok=False
 for attempt in range(1,a.attempts+1):
  results=[];ok=True
  for rec in records:
   url=urllib.parse.urljoin(base,rec['path'])+f'?source={urllib.parse.quote(a.sha)}&attempt={attempt}'
   req=urllib.request.Request(url,headers={'Cache-Control':'no-cache, no-store, max-age=0','Pragma':'no-cache','User-Agent':'MadeByMatt-LundyLoop-Deploy-Proof/2'})
   try:
    with urllib.request.urlopen(req,timeout=30) as response:
     body=response.read();status=response.status;ctype=response.headers.get('Content-Type','')
    match=sha(body)==rec['sha256'];html_ok=not rec['path'].endswith('.html') or 'text/html' in ctype.lower();row={'path':rec['path'],'url':url,'http':status,'content_type':ctype,'expected_sha256':rec['sha256'],'served_sha256':sha(body),'match':match and html_ok}
   except Exception as e:
    row={'path':rec['path'],'url':url,'match':False,'error':str(e)}
   results.append(row);ok=ok and row['match']
  if ok:all_ok=True;break
  if attempt<a.attempts:time.sleep(a.sleep)
 out={'status':'PASS' if all_ok else 'FAIL','base':base,'merge_sha':a.sha,'attempt':attempt,'files':results};print(json.dumps(out,indent=2))
 if a.json_out:a.json_out.parent.mkdir(parents=True,exist_ok=True);a.json_out.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
 return 0 if all_ok else 1
if __name__=='__main__':raise SystemExit(main())
