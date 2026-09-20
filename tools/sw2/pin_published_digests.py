#!/usr/bin/env python3
"""Derive the PUBLISHED digest table in tools/sw2/check_tokens_inert.cjs; never type it.

THE FAULT THIS CLOSES (STOP-P1, SX3). check_tokens_inert.cjs --published fetches the
live origin and requires three routes to hash to a table typed on line 22:
lessons "" and "subject.html", apps "". The SX3 release moved the hub and the
subject page by design, nothing re-derived the table, and the cross-estate
live-proof job went red on main in both estates - "green by absence" while the
pin was current, red by staleness once it was not. A typed copy of a value a
record supplies is failure mode 1 (census_typed_literals.py on the Site); this
is that class in the token checker.

WHERE THE VALUE COMES FROM - CI'S MEASUREMENT, RELAYED. The Site's admission
registry, domain-split/education-publication-admission.json, names every
published path with the digest the pinned publisher produces. It is not a
guess: the Education Pages publication job builds the trees and goes RED when a
built byte differs from its registry entry ("CHANGED <path>"), so a green
publication on main is CI's proof that the served bytes equal the registry. This
tool reads those entries for the three routes and writes them into the table.
A route whose path is missing from the registry is a refusal, never a pass by
absence. A transition pair [previous, current] resolves to CURRENT, and the tool
says so in its output.

BOTH ESTATES, ONE TOOL. The table carries apps and lessons entries in one line
in both estates' copies of check_tokens_inert.cjs, so the tool writes all three
values wherever it runs; the two copies then agree by derivation, not by
mirroring. The gate pins check_tokens_inert.cjs by digest (CATALOGUE_PINS on
Lessons), so a --write is followed by the catalogue pin writer in both gate
copies - regenerate AND pin, never one without the other.

  python3 tools/sw2/pin_published_digests.py --registry PATH --check    report drift, exit 1
  python3 tools/sw2/pin_published_digests.py --registry PATH --write    rewrite the table
  python3 tools/sw2/pin_published_digests.py --self-test                red-proves the check
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECKER = os.path.join('tools', 'sw2', 'check_tokens_inert.cjs')
LINE = re.compile(r'^const PUBLISHED=(\{.*\});$', re.M)
# route -> (registry tree, published path). "" is the hub index of each estate.
ROUTES = {
    'lessons': {'': ('education-lessons', 'index.html'), 'subject.html': ('education-lessons', 'subject.html')},
    'apps': {'': ('education-apps', 'index.html')},
}


def registry_values(registry_path):
    reg = json.load(open(registry_path, encoding='utf-8'))
    trees = reg['trees']
    out, notes = {}, []
    for kind, routes in ROUTES.items():
        out[kind] = {}
        for route, (tree, path) in routes.items():
            value = trees.get(tree, {}).get(path)
            if value is None:
                raise SystemExit(f'REFUSED: {tree}/{path} (route {kind} {route!r}) is not in the registry; '
                                 f'a route the registry does not admit cannot be pinned')
            if isinstance(value, list):
                if len(value) != 2:
                    raise SystemExit(f'REFUSED: {tree}/{path} carries {len(value)} digests; a pair has two')
                notes.append(f'{tree}/{path}: transition pair, CURRENT {value[1][:12]} taken (previous {value[0][:12]})')
                value = value[1]
            if not re.fullmatch(r'[0-9a-f]{64}', value):
                raise SystemExit(f'REFUSED: {tree}/{path} digest is not sha256 hex: {value!r}')
            out[kind][route] = value
    return out, notes


def current_table(checker_path):
    text = open(checker_path, encoding='utf-8').read()
    m = LINE.search(text)
    if not m:
        raise SystemExit(f'REFUSED: no "const PUBLISHED={{...}};" line in {checker_path}')
    return text, m, json.loads(m.group(1))


def registry_head(registry_path):
    try:
        top = subprocess.run(['git', '-C', os.path.dirname(registry_path), 'rev-parse', '--short', 'HEAD'],
                             capture_output=True, text=True)
        return top.stdout.strip() if top.returncode == 0 else 'not a git checkout'
    except OSError:
        return 'git unavailable'


def run(root, registry_path, write, out=print):
    checker = os.path.join(root, CHECKER)
    out(f'scope: table = {os.path.relpath(checker, root)} line "const PUBLISHED=...;" ; source = {registry_path} '
        f'(checkout head {registry_head(registry_path)}), trees.education-lessons/index.html, '
        f'trees.education-lessons/subject.html, trees.education-apps/index.html; a pair resolves to CURRENT')
    wanted, notes = registry_values(registry_path)
    for n in notes:
        out('  ' + n)
    text, m, have = current_table(checker)
    drift = []
    for kind, routes in ROUTES.items():
        for route in routes:
            typed = have.get(kind, {}).get(route)
            derived = wanted[kind][route]
            state = 'equal' if typed == derived else 'DRIFT'
            out(f'  {kind:7} {route or "(hub)":13} typed {str(typed)[:12]:12} derived {derived[:12]}  {state}')
            if typed != derived:
                drift.append((kind, route, typed, derived))
    extra = [(k, r) for k, rs in have.items() for r in rs if r not in ROUTES.get(k, {})]
    if extra:
        out(f'  NOTE: routes typed in the table that this tool does not derive: {extra}')
    if write:
        new_line = 'const PUBLISHED=' + json.dumps(wanted, separators=(',', ':')) + ';'
        if m.group(0) != new_line:
            open(checker, 'w', encoding='utf-8').write(text[:m.start()] + new_line + text[m.end():])
            out(f'  wrote {len(drift)} re-derived value(s); sha256({os.path.relpath(checker, root)}) is now '
                f'{hashlib.sha256(open(checker, "rb").read()).hexdigest()[:12]} - re-pin it in both gate copies')
        else:
            out('  table already equals the registry; nothing written')
        return 0
    if drift:
        out(f'RESULT: RED {len(drift)} of {sum(len(r) for r in ROUTES.values())} routes drifted from the registry')
        return 1
    out('RESULT: PASS every route equals its registry entry')
    return 0


def self_test():
    problems = []
    tmp = tempfile.mkdtemp(prefix='pubpin-')
    try:
        root = os.path.join(tmp, 'estate')
        os.makedirs(os.path.join(root, 'tools', 'sw2'))
        reg = {'trees': {'education-lessons': {'index.html': 'a' * 64, 'subject.html': 'b' * 64},
                         'education-apps': {'index.html': ['c' * 64, 'd' * 64]}}}
        rp = os.path.join(tmp, 'registry.json')
        json.dump(reg, open(rp, 'w'))
        good = {'apps': {'': 'd' * 64}, 'lessons': {'': 'a' * 64, 'subject.html': 'b' * 64}}
        checker = os.path.join(root, CHECKER)

        def write_checker(table):
            open(checker, 'w').write('// head\nconst X=1;\nconst PUBLISHED=' + json.dumps(table, separators=(',', ':')) + ';\nconst Y=2;\n')

        def case(name, table, expect_rc, registry=rp):
            write_checker(table)
            rc = run(root, registry, False, out=lambda *_: None)
            ok = rc == expect_rc
            print(f'  {"PASS" if ok else "FAIL"}  {name}: --check exit {rc}, expected {expect_rc}')
            if not ok:
                problems.append(name)

        case('positive control: table equals the registry (pair resolved to CURRENT)', good, 0)
        planted = json.loads(json.dumps(good)); planted['lessons'][''] = 'f' * 64
        case('planted digest on lessons hub is RED', planted, 1)
        planted = json.loads(json.dumps(good)); planted['apps'][''] = 'c' * 64
        case('the PREVIOUS half of a pair is RED (served is CURRENT)', planted, 1)
        planted = json.loads(json.dumps(good)); del planted['lessons']['subject.html']
        case('a route missing from the table is RED', planted, 1)
        # --write repairs, and --check then passes
        write_checker(planted)
        run(root, rp, True, out=lambda *_: None)
        rc = run(root, rp, False, out=lambda *_: None)
        ok = rc == 0 and LINE.search(open(checker).read()) and open(checker).read().startswith('// head\nconst X=1;\n') and open(checker).read().endswith('const Y=2;\n')
        print(f'  {"PASS" if ok else "FAIL"}  --write repairs the table in place, the rest of the file untouched, --check then passes')
        if not ok:
            problems.append('write')
        # registry missing a path refuses
        bad = {'trees': {'education-lessons': {'index.html': 'a' * 64}, 'education-apps': {'index.html': 'd' * 64}}}
        bp = os.path.join(tmp, 'bad.json'); json.dump(bad, open(bp, 'w'))
        write_checker(good)
        try:
            run(root, bp, False, out=lambda *_: None); refused = False
        except SystemExit as e:
            refused = 'REFUSED' in str(e)
        print(f'  {"PASS" if refused else "FAIL"}  a route the registry does not admit is a refusal, never a pass by absence')
        if not refused:
            problems.append('refusal')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if problems:
        print('SELF-TEST FAIL:', problems)
        return 1
    print('SELF-TEST PASS: a planted digest, a previous-half pair, a missing route each redden --check; --write repairs; an unadmitted route refuses')
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--registry', help="the Site's domain-split/education-publication-admission.json")
    ap.add_argument('--root', default=ROOT, help='this estate checkout (default: the one this file is in)')
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--check', action='store_true')
    g.add_argument('--write', action='store_true')
    g.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.registry:
        ap.error('--registry PATH is required (or --self-test)')
    return run(os.path.abspath(a.root), os.path.abspath(a.registry), a.write)


if __name__ == '__main__':
    sys.exit(main())
