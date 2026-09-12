"""Local PIN1 controls. These do not substitute for GitHub event experiments."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import derive_triggers as d

FIXTURE = '''name: fixture
on:
  pull_request:
    branches: [main]
    paths:
      - index.html
  push:
    branches: [main]
    paths:
      - index.html
  workflow_run:
    workflows: [publication]
    types: [completed]
    branches: [main]
  schedule:
    - cron: '9 7 * * *'
  workflow_dispatch:
permissions:
  contents: read
jobs:
  verify:
    if: github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success'
    runs-on: ubuntu-latest
    steps:
      - run: echo unchanged
'''


class TriggerControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.gate = SimpleNamespace(
            detect_kind=lambda _: 'apps',
            CANONICAL_HASHES={'assets/shared.css': 'digest'},
            MANIFEST_PINS={'apps.json': 'digest', 'resources.json': 'digest'},
            LUNDYLOOP_CI_PINS={d.D: 'digest', 'tools/lundyloop/proof.py': 'digest'},
            PUBLICATION_CALLER_PATH='.github/workflows/education-pages.yml',
        )
        for path in ('apps.json', 'assets/shared.css', 'tools/lundyloop/proof.py',
                     d.C, d.D, self.gate.PUBLICATION_CALLER_PATH):
            self.put(path, FIXTURE if path in d.WORKFLOWS else 'fixture')

    def put(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')

    def report(self):
        return d.inventory(self.root, self.gate)

    def rendered(self, report=None):
        report = report or self.report()
        return {path: d.render(FIXTURE, data['expected_triggers'])
                for path, data in report['workflows'].items()}

    def test_each_gate_covers_every_assertion_in_both_events(self):
        report = self.report()
        texts = self.rendered(report)
        self.assertEqual(d.check(texts, report), [])
        for path, text in texts.items():
            for event in d.EVENTS:
                self.assertTrue(set(report['asserted']) <= set(d.read_paths(text, event)))
            self.assertEqual(text, d.render(text, report['workflows'][path]['expected_triggers']))

    def test_non_path_bytes_including_other_events_preserved(self):
        for rendered in self.rendered().values():
            normalized = []
            for text in (FIXTURE, rendered):
                for event in d.EVENTS:
                    begin, end = d.event_paths_span(text, event)
                    text = text[:begin] + '      - TOKEN\n' + text[end:]
                normalized.append(text)
            self.assertEqual(*normalized)

    def test_each_gate_independently_rejects_a_missing_trigger(self):
        report = self.report()
        for workflow in d.WORKFLOWS:
            for event in d.EVENTS:
                texts = self.rendered(report)
                original = texts[workflow]
                begin, end = d.event_paths_span(original, event)
                mutated = original[begin:end].replace("      - 'apps.json'\n", '')
                self.assertNotEqual(mutated, original[begin:end])
                texts[workflow] = original[:begin] + mutated + original[end:]
                self.assertTrue(d.check(texts, copy.deepcopy(report)))

    def test_new_pin_requires_regeneration_in_every_gate(self):
        old = self.rendered()
        target = 'new/registry-input.json'
        self.gate.LUNDYLOOP_CI_PINS[target] = 'digest'
        self.put(target, 'fixture')
        report = self.report()
        self.assertIn(target, report['asserted'])
        self.assertTrue(d.check(old, copy.deepcopy(report)))
        new = self.rendered(report)
        self.assertEqual(d.check(new, report), [])
        for text in new.values():
            for event in d.EVENTS:
                self.assertIn(target, d.read_paths(text, event))

    def test_removed_pin_retires_its_exact_trigger(self):
        old = self.rendered()
        target = 'tools/lundyloop/proof.py'
        del self.gate.LUNDYLOOP_CI_PINS[target]
        report = self.report()
        self.assertNotIn(target, report['asserted'])
        self.assertTrue(d.check(old, copy.deepcopy(report)))
        new = self.rendered(report)
        for text in new.values():
            for event in d.EVENTS:
                self.assertNotIn(target, d.read_paths(text, event))
        self.assertEqual(d.check(new, report), [])

    def test_deleted_pin_keeps_dependency_and_fails(self):
        target = 'tools/lundyloop/proof.py'
        (self.root / target).unlink()
        self.assertFalse((self.root / target).exists())
        report = self.report()
        self.assertIn(target, report['asserted'])
        self.assertTrue(d.check(self.rendered(report), report))

    def test_deleted_manifest_cannot_erase_dependency(self):
        (self.root / 'apps.json').unlink()
        report = self.report()
        self.assertIn('apps.json', report['asserted'])
        self.assertTrue(d.check(self.rendered(report), report))

    def test_existing_payload_patterns_stay_only_in_gate_d(self):
        texts = self.rendered()
        for event in d.EVENTS:
            self.assertTrue(d.LEGACY_GLOBS <= set(d.read_paths(texts[d.D], event)))
            self.assertFalse(d.LEGACY_GLOBS & set(d.read_paths(texts[d.C], event)))
        for deps in d.WORKFLOWS.values():
            self.assertTrue({d.GATE, d.SELF, d.CONTROLS} <= deps)

    def test_unrelated_change_leaves_each_gate_dormant(self):
        for text in self.rendered().values():
            for event in d.EVENTS:
                paths = d.read_paths(text, event)
                self.assertNotIn('docs/orders/pin1-dormant.txt', paths)
                self.assertNotIn('**', paths)

    def test_unrelated_trigger_or_duplicate_is_red(self):
        for mutation in ("      - 'unrelated.txt'\n", "      - '**'\n",
                         "      - 'apps.json'\n"):
            for workflow in d.WORKFLOWS:
                texts = self.rendered()
                old = texts[workflow]
                texts[workflow] = old.replace(d.END, mutation + d.END)
                self.assertNotEqual(texts[workflow], old)
                self.assertTrue(d.check(texts, self.report()))

    def test_unsafe_registry_paths_refused_even_if_existing_payload_glob(self):
        for target in ('**', 'apps/*.html', '../a', '/a', 'a//b', 'a?b', '!a',
                       'a\nb', *d.LEGACY_GLOBS):
            with self.subTest(target=target):
                gate = copy.deepcopy(self.gate)
                gate.LUNDYLOOP_CI_PINS[target] = 'digest'
                with self.assertRaises(ValueError):
                    d.inventory(self.root, gate)
        self.assertEqual(d.exact_path("A lesson (one)/pupil's.json"), "A lesson (one)/pupil's.json")

    def test_wrong_kind_empty_or_incomplete_registry_refused(self):
        for attr in ('CANONICAL_HASHES', 'LUNDYLOOP_CI_PINS', 'MANIFEST_PINS'):
            gate = copy.deepcopy(self.gate)
            getattr(gate, attr).clear()
            with self.assertRaises(ValueError):
                d.inventory(self.root, gate)
        self.gate.detect_kind = lambda _: 'lessons'
        with self.assertRaises(ValueError):
            self.report()

    def test_malformed_second_workflow_causes_no_partial_write(self):
        texts = {d.C: FIXTURE, d.D: FIXTURE.replace('  push:', '  other:')}
        before = {path: (self.root / path).read_bytes() for path in d.WORKFLOWS}
        with self.assertRaises(ValueError):
            d.regenerate(self.root, texts, self.report())
        self.assertEqual(before, {path: (self.root / path).read_bytes() for path in d.WORKFLOWS})

    def test_digest_only_update_does_not_change_generated_workflow_bytes(self):
        before = self.rendered()
        self.gate.LUNDYLOOP_CI_PINS[d.D] = 'reviewed new workflow digest'
        self.assertEqual(before, self.rendered())

    def test_ambiguous_events_refused(self):
        for bad in (FIXTURE.replace('  push:', '  other:'),
                    FIXTURE.replace('    paths:', '    paths-ignore:', 1),
                    'on:\n  push:\n' + FIXTURE):
            with self.assertRaises(ValueError):
                d.render(bad, self.report()['workflows'][d.C]['expected_triggers'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
