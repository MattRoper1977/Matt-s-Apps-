"""Real payload, one planted served-byte defect, restored; provenance rejections."""
import argparse
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.parse
import urllib.request
import verify_live_bytes as gate

ROOT = Path(__file__).resolve().parents[2]
PUBLICATION = None

class Controls(unittest.TestCase):
    def setUp(self):
        self.records = gate.source_records(ROOT)
        self.wanted = 'a' * 40
        self.publication = {'source_sha': self.wanted, 'publication_sha': self.wanted,
                            'deployment': 'success', 'root': str(PUBLICATION or ROOT)}
        self.expected = gate.expected_records(self.records, self.publication, self.wanted)

    def test_real_planted_restored(self):
        bodies = {row['path']: (Path(self.publication['root']) / row['path']).read_bytes() for row in self.records}
        def transport(url):
            path = urllib.parse.unquote(urllib.parse.urlsplit(url).path.removeprefix('/Matt-s-Apps-/'))
            return 200, 'text/html' if path.endswith('.html') else 'image/jpeg', bodies[path]
        self.assertTrue(gate.check_once(self.expected, self.wanted, 1, transport)[0])
        key = self.records[0]['path']
        original = bodies[key]
        bodies[key] += b'x'
        passed, rows = gate.check_once(self.expected, self.wanted, 2, transport)
        self.assertFalse(passed)
        self.assertEqual([row['path'] for row in rows if not row['match']], [key])
        bodies[key] = original
        self.assertTrue(gate.check_once(self.expected, self.wanted, 3, transport)[0])
        print('FIRING CONTROL real PASS / one served byte FAIL / restored PASS; payloads', len(self.records))

    def test_other_source_or_failed_deploy_cannot_borrow_artifact(self):
        for mutation in [{'source_sha': 'b'*40}, {'publication_sha': 'b'*40}, {'deployment': 'skipped'}]:
            with self.assertRaises(ValueError):
                gate.expected_records(self.records, {**self.publication, **mutation}, self.wanted)

    def test_raw_source_mismatch_is_rejected(self):
        original = Path.read_bytes
        target = (ROOT / self.records[0]['path']).resolve()
        def mutate(path):
            data = original(path)
            return data + b'x' if path.resolve() == target else data
        with patch.object(Path, 'read_bytes', mutate), self.assertRaisesRegex(ValueError, 'Raw source manifest mismatch'):
            gate.source_records(ROOT)
        self.assertEqual(gate.source_records(ROOT), self.records)

    def test_status_mime_and_redirect_are_rejected(self):
        rec = self.expected[0]
        body = (Path(self.publication['root']) / rec['path']).read_bytes()
        for status, mime in [(404, 'text/html'), (302, 'text/html'), (200, 'text/plain')]:
            self.assertFalse(gate.check_once([rec], self.wanted, 1, lambda url: (status, mime, body))[0])
        for url in ['https://example.com/', gate.BASE + 'other.html', gate.BASE.replace('https:', 'http:')]:
            with self.assertRaises(ValueError):
                gate.NoRedirect().redirect_request(urllib.request.Request(gate.BASE), None, 302, 'Found', {}, url)

    def test_conflicting_publisher_pin_is_rejected(self):
        actual = gate.builder_ref(ROOT)
        original = Path.read_text
        with patch.object(Path, 'read_text', lambda path: original(path).replace('builder_ref: '+actual, 'builder_ref: '+'b'*40)):
            with self.assertRaises(ValueError): gate.builder_ref(ROOT)


# Evaluate the small Actions expression subset used by the actual scheduling YAML.
# Tokens are restricted before evaluation; no calls or arbitrary Python are accepted.
def actions_value(expression, github):
    import re
    expression = expression.strip()
    if expression.startswith('${{'):
        expression = expression[3:-2].strip()
    pattern = re.compile(r"\s*('(?:[^']|'')*'|github(?:\.[A-Za-z_][A-Za-z_0-9]*)+|&&|\|\||==|!=|[()])")
    parts, position = [], 0
    while position < len(expression):
        match = pattern.match(expression, position)
        if not match:
            raise ValueError('Unsupported scheduling expression at ' + expression[position:])
        token = match.group(1)
        position = match.end()
        if token.startswith('github.'):
            value = github
            for key in token.split('.')[1:]:
                value = value.get(key, '') if isinstance(value, dict) else ''
            parts.append(repr(value))
        elif token.startswith("'"):
            parts.append(repr(token[1:-1].replace("''", "'")))
        else:
            parts.append({'&&': 'and', '||': 'or'}.get(token, token))
    return eval(' '.join(parts), {'__builtins__': {}}, {})


def schedule_errors(document):
    import re
    errors = []
    trigger = document.get('on', {}).get('workflow_run', {})
    if trigger != {'workflows': ['Education Pages publication'], 'types': ['completed'], 'branches': ['main']}:
        errors.append('Completion trigger must name the main publisher')
    if not {'pull_request', 'push', 'workflow_dispatch'} <= set(document.get('on', {})):
        errors.append('Existing fixture triggers were removed')
    jobs = document['jobs']
    if jobs['live-bytes'].get('needs') != 'verify':
        errors.append('Live proof must retain the complete fixture prerequisite')
    repo = 'MattRoper1977/Matt-s-Apps-'
    valid = {'event_name': 'workflow_run', 'repository': repo, 'sha': 'b'*40,
             'ref': 'refs/heads/main', 'event': {'action': 'completed', 'workflow_run': {
                 'id': 101, 'status': 'completed', 'conclusion': 'success', 'head_branch': 'main',
                 'head_repository': {'full_name': repo}, 'head_sha': 'a'*40, 'event': 'push'}}}
    cases = [(valid, True, True)]
    for field, values in {'status': ['queued', 'in_progress'],
                          'conclusion': ['failure', 'cancelled', 'skipped', ''],
                          'head_branch': ['feature'], 'event': ['pull_request']}.items():
        for value in values:
            context = copy.deepcopy(valid)
            context['event']['workflow_run'][field] = value
            cases.append((context, False, False))
    context = copy.deepcopy(valid)
    context['event']['workflow_run']['head_repository']['full_name'] = 'another/repository'
    cases.append((context, False, False))
    context = copy.deepcopy(valid)
    context['event']['action'] = 'requested'
    cases.append((context, False, False))
    for event in ['pull_request', 'push', 'workflow_dispatch']:
        context = copy.deepcopy(valid)
        context['event_name'], context['event'] = event, {'pull_request': {'number': 12}} if event == 'pull_request' else {}
        cases.append((context, True, False))
    context = copy.deepcopy(valid)
    context['event']['workflow_run']['event'] = 'workflow_dispatch'
    cases.append((context, True, True))
    for context, fixture, live in cases:
        for job, expected in [('verify', fixture), ('live-bytes', live)]:
            if bool(actions_value(jobs[job].get('if', ''), context)) != expected:
                errors.append('Wrong '+job+' decision for '+repr(context))
    for job in ['verify', 'live-bytes']:
        checkout = [s for s in jobs[job]['steps'] if s.get('uses', '').startswith('actions/checkout@')][0]
        if actions_value(checkout.get('with', {}).get('ref', ''), valid) != 'a'*40:
            errors.append(job+' checkout used current HEAD instead of the completed source')
    fixture_checkout = jobs['verify']['steps'][0]['with']['ref']
    for event in ['pull_request', 'push', 'workflow_dispatch']:
        context = {**valid, 'event_name': event, 'event': {}}
        if actions_value(fixture_checkout, context) != 'b'*40:
            errors.append('Fixture checkout no longer uses the triggering revision')
    proof = next(s for s in jobs['live-bytes']['steps'] if s.get('name') == 'Exact published-byte proof')
    if (actions_value(proof.get('env', {}).get('PUBLICATION_SOURCE_SHA', ''), valid) != 'a'*40
            or '--sha "$PUBLICATION_SOURCE_SHA"' not in proof['run'] or '--sha "$GITHUB_SHA"' in proof['run']):
        errors.append('Byte proof must name the checked-out upstream source')
    if bool(actions_value(document['concurrency']['cancel-in-progress'], valid)):
        errors.append('A repeated publication completion can cancel active live proof')
    group = document['concurrency']['group']
    def expanded(context):
        return re.sub(r'\$\{\{.*?\}\}', lambda m: str(actions_value(m.group(), context)), group)
    groups = {expanded(valid)}
    for event in ['push', 'pull_request']:
        groups.add(expanded({**valid, 'event_name': event, 'event': {'pull_request': {'number': 12}}}))
    other = copy.deepcopy(valid)
    other['event']['workflow_run']['id'] = 102
    groups.add(expanded(other))
    if len(groups) != 4:
        errors.append('Independent publication and PR/push runs can cancel one another')
    return errors


class SchedulingControls(unittest.TestCase):
    def test_actual_workflow_real_planted_restored(self):
        import yaml
        path = ROOT / '.github/workflows/verify-lundyloop-professional-os.yml'
        document = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(schedule_errors(document), [])
        scratch = copy.deepcopy(document)
        original = scratch['jobs']['live-bytes']['if']
        scratch['jobs']['live-bytes']['if'] = "github.event_name == 'push' && github.ref == 'refs/heads/main'"
        self.assertTrue(schedule_errors(scratch), 'Prepublication live start escaped the planted control')
        scratch['jobs']['live-bytes']['if'] = original
        self.assertEqual(schedule_errors(scratch), [])
        print('SCHEDULING CONTROL actual workflow PASS / one premature live trigger FAIL / restored PASS; upstream A != current HEAD B')

    def test_wrong_source_and_publication_origin_are_rejected(self):
        import yaml
        document = yaml.load((ROOT / '.github/workflows/verify-lundyloop-professional-os.yml').read_text(), Loader=yaml.BaseLoader)
        mutations = [
            lambda d: d['jobs']['live-bytes']['steps'][0]['with'].update(ref='${{ github.sha }}'),
            lambda d: d['jobs']['verify']['steps'][0]['with'].update(ref='${{ github.sha }}'),
            lambda d: d['jobs']['live-bytes'].update(needs='unrelated'),
            lambda d: d['on']['workflow_run'].update(workflows=['Unrelated workflow']),
        ]
        for mutate in mutations:
            scratch = copy.deepcopy(document)
            mutate(scratch)
            self.assertTrue(schedule_errors(scratch))
            self.assertEqual(schedule_errors(document), [])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--publication-root', type=Path)
    args, rest = parser.parse_known_args()
    PUBLICATION = args.publication_root
    unittest.main(argv=[__file__] + rest)
