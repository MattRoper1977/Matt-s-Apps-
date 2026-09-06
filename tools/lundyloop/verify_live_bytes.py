#!/usr/bin/env python3
"""Prove raw source identity, then exact successful publication bytes at the origin."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

BASE = 'https://madebymatt.uk/Matt-s-Apps-/'
MANIFEST = '_release-docs/lundyloop-professional-os-v2/PAYLOAD_MANIFEST.json'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def builder_ref(root):
    text = (root / '.github/workflows/education-pages.yml').read_text()
    uses = re.findall(r'uses:\s*MattRoper1977/mattroper1977\.github\.io/\.github/workflows/education-publication\.yml@([a-f0-9]{40})\s*$', text, re.M)
    refs = re.findall(r'^\s*builder_ref:\s*([a-f0-9]{40})\s*$', text, re.M)
    if len(uses) != 1 or refs != uses:
        raise ValueError('Publisher workflow and builder_ref must bind the same immutable Site commit')
    return uses[0]

def load_provenance(root, site):
    actual = subprocess.check_output(['git', '-C', str(site), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != builder_ref(root):
        raise ValueError('Site provenance helper checkout is not the Apps publisher pin')
    spec = importlib.util.spec_from_file_location('lundy_publications', site / 'tools/lib/publication_artifacts.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def source_records(root):
    manifest = json.loads((root / MANIFEST).read_text())
    records = [r for r in manifest['records'] if r['path'].endswith(('.html', '.jpg'))]
    seen = set()
    if not records:
        raise ValueError('Empty source payload census')
    for rec in records:
        path = Path(rec['path'])
        if path.is_absolute() or '..' in path.parts or '\\' in str(path) or rec['path'] in seen:
            raise ValueError('Unsafe or duplicate source payload path')
        seen.add(rec['path'])
        data = (root / path).read_bytes()
        if sha(data) != rec['sha256'] or len(data) != rec['bytes']:
            raise ValueError('Raw source manifest mismatch: ' + rec['path'])
    return records

def expected_records(records, publication, wanted):
    if publication['source_sha'] != wanted or publication['publication_sha'] != wanted or publication['deployment'] != 'success':
        raise ValueError('Publication does not bind the exact Apps source and successful deployment')
    root = Path(publication['root']).resolve()
    result = []
    for rec in records:
        path = (root / rec['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('Publication payload missing or escaping: ' + rec['path'])
        data = path.read_bytes()
        result.append({'path': rec['path'], 'source_sha256': rec['sha256'],
                       'published_sha256': sha(data), 'published_bytes': len(data)})
    return result

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError('Origin proof refuses HTTP redirect ' + str(code))

def fetch(url):
    request = urllib.request.Request(url, headers={
        'Cache-Control': 'no-cache, no-store, max-age=0', 'Pragma': 'no-cache',
        'User-Agent': 'MadeByMatt-LundyLoop-Deploy-Proof/3'})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
        body = response.read(8_000_001)
        if len(body) > 8_000_000:
            raise ValueError('Oversized live payload')
        return response.status, response.headers.get('Content-Type', ''), body

def check_once(records, wanted, attempt, transport=fetch):
    results = []
    for rec in records:
        url = BASE + urllib.parse.quote(rec['path'], safe='/') + f'?source={wanted}&attempt={attempt}'
        row = {**rec, 'url': url, 'match': False}
        try:
            status, ctype, body = transport(url)
            mime = 'text/html' if rec['path'].endswith('.html') else 'image/jpeg'
            row.update(http=status, content_type=ctype, served_sha256=sha(body), served_bytes=len(body))
            row['match'] = status == 200 and ctype.split(';')[0].strip().lower() == mime and sha(body) == rec['published_sha256']
        except Exception as exc:
            row['error'] = str(exc)
        results.append(row)
    return all(row['match'] for row in results), results

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path('.'))
    parser.add_argument('--site-root', type=Path, default=Path('_reference/site'))
    parser.add_argument('--print-builder-ref', action='store_true')
    parser.add_argument('--base', default=BASE)
    parser.add_argument('--sha')
    parser.add_argument('--attempts', type=int, default=30)
    parser.add_argument('--sleep', type=float, default=10)
    parser.add_argument('--json-out', type=Path)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    if args.print_builder_ref:
        print(builder_ref(root))
        return 0
    out = {'status': 'INCONCLUSIVE', 'base': args.base, 'merge_sha': args.sha, 'files': []}
    code = 2
    try:
        if args.base != BASE or not re.fullmatch('[a-f0-9]{40}', args.sha or ''):
            raise ValueError('Exact canonical origin and immutable source SHA required')
        if not 1 <= args.attempts <= 60 or not 0 <= args.sleep <= 10:
            raise ValueError('Retry bounds exceeded')
        provenance = load_provenance(root, args.site_root.resolve())
        if provenance.head(root) != args.sha:
            raise ValueError('Source checkout differs from requested Apps SHA')
        records = source_records(root)
        with tempfile.TemporaryDirectory(prefix='lundy-publication-') as temp:
            publication = provenance.prepare_one('apps', args.sha, Path(temp), provenance.GitHub(time.monotonic()+240))
            out['publication'] = publication
            out['builder_sha'] = builder_ref(root)
            expected = expected_records(records, publication, args.sha)
            live_deadline = time.monotonic() + 600
            for attempt in range(1, args.attempts+1):
                passed, results = check_once(expected, args.sha, attempt)
                out.update(status='PASS' if passed else 'FAIL', attempt=attempt, files=results)
                code = 0 if passed else 1
                if passed or time.monotonic() >= live_deadline:
                    break
                if attempt < args.attempts:
                    time.sleep(args.sleep)
    except Exception as exc:
        out.update(status='INCONCLUSIVE', error=str(exc))
        code = 2
    rendered = json.dumps(out, indent=2) + '\n'
    print(rendered, end='')
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered)
    return code

if __name__ == '__main__':
    raise SystemExit(main())
