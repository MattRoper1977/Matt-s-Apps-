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

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--publication-root', type=Path)
    args, rest = parser.parse_known_args()
    PUBLICATION = args.publication_root
    unittest.main(argv=[__file__] + rest)
