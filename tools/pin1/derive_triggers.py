#!/usr/bin/env python3
"""PIN1: derive both Apps gates' paths from the registry they assert.

--write materializes reviewed paths; --check is read-only and fails on drift.
Gate D is itself pinned: after generation its digest must be reviewed in BOTH
shared checker copies. Generating paths never moves a digest or weakens a gate.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import sys

GATE = 'tools/verify_cross_estate_unification.py'
SELF = 'tools/pin1/derive_triggers.py'
CONTROLS = 'tools/pin1/test_derive_triggers.py'
C = '.github/workflows/mbm-cross-estate-unification.yml'
D = '.github/workflows/verify-lundyloop-professional-os.yml'
# Preserve the pre-PIN1 non-digest subjects. Only these three EXISTING payload
# patterns may contain globs; registry paths and new checker paths must be exact.
LEGACY_GLOBS = frozenset({
    'LundyLoop_Professional_OS/**',
    '_release-docs/lundyloop-professional-os-v2/**',
    'tools/lundyloop/**',
})
COMMON = {GATE, SELF, CONTROLS, 'index.html'}
WORKFLOWS = {
    C: COMMON | {C, 'tools/verify_cross_estate_browser.mjs',
                 'docs/MBM_CROSS_ESTATE_UNIFICATION.md'},
    D: COMMON | {D, 'LundyLoop_Professional_OS.html'} | LEGACY_GLOBS,
}
EVENTS = ('pull_request', 'push')
BEGIN = '      # BEGIN PIN1 DERIVED PATHS'
END = '      # END PIN1 DERIVED PATHS'


def load_gate(root: Path):
    spec = importlib.util.spec_from_file_location('pin1_apps_gate', root / GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exact_path(value: str) -> str:
    if (not isinstance(value, str) or not value or value.startswith('/')
            or any(c in value for c in '*?[]!+\\\r\n')
            or any(p in ('', '.', '..') for p in value.split('/'))
            or str(PurePosixPath(value)) != value):
        raise ValueError(f'not an exact safe registry path: {value!r}')
    return value


def inventory(root: Path, gate=None) -> dict:
    gate = gate or load_gate(root)
    if gate.detect_kind(root) != 'apps':
        raise ValueError('this generator requires the Apps checkout')
    if 'apps.json' not in gate.MANIFEST_PINS:
        raise ValueError('Apps manifest pin missing')
    registries = {
        'CANONICAL_HASHES': set(gate.CANONICAL_HASHES),
        # The shared checker skips the other repository's absent manifest.
        # Keep apps.json required even if deleted, never erase its dependency.
        'MANIFEST_PINS': {'apps.json'} | {
            p for p in gate.MANIFEST_PINS if (root / p).is_file()},
        'LUNDYLOOP_CI_PINS': set(gate.LUNDYLOOP_CI_PINS),
        'PUBLICATION_CALLER': {gate.PUBLICATION_CALLER_PATH},
    }
    if any(not paths for paths in registries.values()) or D not in registries['LUNDYLOOP_CI_PINS']:
        raise ValueError('empty/incomplete Apps pin registry is unmeasured')
    asserted = set().union(*registries.values())
    for path in asserted:
        exact_path(path)
    workflows = {}
    for workflow, existing in WORKFLOWS.items():
        for path in existing - LEGACY_GLOBS:
            exact_path(path)
        expected = asserted | existing
        workflows[workflow] = {
            'expected_triggers': sorted(expected),
            'non_pin_dependencies': sorted(expected - asserted),
        }
    return {
        'kind': 'apps', 'asserted_count': len(asserted),
        'asserted': sorted(asserted),
        'registry_counts': {key: len(paths) for key, paths in registries.items()},
        'rows': [{'path': path, 'registries': sorted(
            key for key, paths in registries.items() if path in paths)}
            for path in sorted(asserted)],
        'missing_asserted_files': sorted(p for p in asserted if not (root / p).is_file()),
        'workflows': workflows,
    }


def event_paths_span(text: str, event: str) -> tuple[int, int]:
    # Same bounded explicit-block walker used by Lessons #517. Refuse alternate
    # or ambiguous syntax; do not reserialize conditions, permissions or jobs.
    on = re.search(r'^on:\n(?P<body>(?:[ \t].*\n|\n|#.*\n)*)', text, re.M)
    if not on or len(re.findall(r'^on:', text, re.M)) != 1:
        raise ValueError('one explicit top-level on block required')
    body = on.group('body')
    matches = list(re.finditer(r'^  ' + re.escape(event) + r':\n', body, re.M))
    if len(matches) != 1:
        raise ValueError(f'one explicit {event} event required')
    start = matches[0].end()
    tail = body[start:]
    next_event = re.search(r'^  [^ #\s][^\n]*:', tail, re.M)
    stop = start + (next_event.start() if next_event else len(tail))
    block = body[start:stop]
    if 'paths-ignore:' in block:
        raise ValueError(f'{event}: paths-ignore not supported')
    paths = list(re.finditer(r'^    paths:\n', block, re.M))
    if len(paths) != 1:
        raise ValueError(f'one explicit {event} paths block required')
    content_start = paths[0].end()
    cursor = content_start
    for line in block[content_start:].splitlines(keepends=True):
        if not line.startswith('      '):
            break
        if not (line.startswith('      - ') or line.lstrip().startswith('#')):
            raise ValueError(f'{event}: unexpected paths syntax {line!r}')
        cursor += len(line)
    if cursor == content_start:
        raise ValueError(f'{event}: empty paths block')
    offset = on.start('body') + start
    return offset + content_start, offset + cursor


def render(text: str, paths: list[str]) -> str:
    for path in paths:
        if path not in LEGACY_GLOBS:
            exact_path(path)
    generated = BEGIN + '\n' + ''.join(
        "      - '" + p.replace("'", "''") + "'\n" for p in paths) + END + '\n'
    for event in EVENTS:
        begin, end = event_paths_span(text, event)
        text = text[:begin] + generated + text[end:]
    return text


def read_paths(text: str, event: str) -> list[str]:
    begin, end = event_paths_span(text, event)
    values = []
    for line in text[begin:end].splitlines():
        if line.startswith('      - '):
            value = line[len('      - '):]
            if value.startswith("'") and value.endswith("'"):
                value = value[1:-1].replace("''", "'")
            elif value.startswith('"'):
                value = json.loads(value)
            values.append(value)
    return values


def check(texts: dict[str, str], report: dict) -> list[str]:
    errors = []
    asserted = set(report['asserted'])
    for workflow, data in report['workflows'].items():
        expected = set(data['expected_triggers'])
        text = texts[workflow]
        data['events'] = {}
        for event in EVENTS:
            values = read_paths(text, event)
            actual = set(values)
            data['events'][event] = {
                'actual_triggers': values,
                'asserted_not_exact_triggered': sorted(asserted - actual),
                'triggered_not_digest_asserted': sorted(actual - asserted),
            }
            if actual != expected or len(values) != len(actual):
                errors.append(f'{workflow} {event}: stale trigger set; '
                              f'missing={sorted(expected - actual)!r}; '
                              f'unexpected={sorted(actual - expected)!r}')
        if text != render(text, data['expected_triggers']):
            errors.append(f'{workflow}: generated paths stale; run {SELF} --write')
    if report['missing_asserted_files']:
        errors.append('asserted inputs missing: ' + repr(report['missing_asserted_files']))
    return errors


def regenerate(root: Path, texts: dict[str, str], report: dict) -> None:
    if report['missing_asserted_files']:
        raise ValueError('refusing generation with missing asserted inputs')
    # Validate BOTH outputs before any write. Never leave the first rewritten
    # because the second workflow had an unsupported syntax shape.
    outputs = {path: render(texts[path], data['expected_triggers'])
               for path, data in report['workflows'].items()}
    for path, content in outputs.items():
        (root / path).write_text(content, encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        report = inventory(args.root)
        texts = {path: (args.root / path).read_text('utf-8') for path in WORKFLOWS}
        if args.write:
            regenerate(args.root, texts, report)
            texts = {path: (args.root / path).read_text('utf-8') for path in WORKFLOWS}
        errors = check(texts, report)
        report.update(errors=errors, verdict='FAIL' if errors else 'PASS')
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        for path, data in report['workflows'].items():
            print(f"PIN1 {report['verdict']} {path}: {report['asserted_count']} asserted; "
                  f"{len(data['expected_triggers'])} triggers per PR/push; "
                  f"{len(data['non_pin_dependencies'])} retained/checker dependencies")
        for error in errors:
            print(error, file=sys.stderr)
        return int(bool(errors))
    except (OSError, ValueError, KeyError, AttributeError) as exc:
        print(f'PIN1 UNMEASURED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
