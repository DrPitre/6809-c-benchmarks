import hashlib
import json
from pathlib import Path
import sys
import unittest
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from matrix import cmoc_version_comparison, render
from assembly_report import publish_cmoc_diffs, cmoc_diff_url


class HistoryTests(unittest.TestCase):
    def test_preserved_snapshot_is_unchanged_and_uses_old_release(self):
        root = Path(__file__).resolve().parents[1] / 'history/cmoc-0.1.99'
        metadata = json.loads((root / 'snapshot.json').read_text())
        data = (root / 'results.json').read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), metadata['results_sha256'])
        reports = json.loads(data)
        cmoc = [r for r in reports if r['compiler'] == 'CMOC']
        self.assertEqual(len(cmoc), 4)
        self.assertTrue(all('0.1.99' in r['version'] for r in cmoc))
        _, document = render(reports, historical=True)
        self.assertIn('Historical snapshot: CMOC 0.1.99', document)

    def test_deltas_require_passing_matching_workloads(self):
        old = {'compiler': 'CMOC', 'suite': 'kr16', 'flags': '-O2',
               'rows': [{'benchmark': 'crc16', 'status': 'PASS', 'source_sha256': 'same',
                         'harness_bytes': 109, 'code_bytes': 100, 'instructions': 1000}]}
        new = dict(old, rows=[dict(old['rows'][0], code_bytes=90, instructions=950)])
        cells = cmoc_version_comparison([new], [old])[0]
        self.assertEqual(len(cells), 4)
        self.assertEqual(cells[2], '-10')
        self.assertEqual(cells[3], '-50')
        self.assertEqual(cmoc_version_comparison([old], [old]), [])
        for changes in ({'source_sha256': 'different'}, {'status': 'FAIL'}, {'harness_bytes': 113}):
            new['rows'] = [dict(old['rows'][0], **changes)]
            self.assertEqual(cmoc_version_comparison([new], [old]), [])

    def test_changed_row_links_to_highlighted_two_version_assembly(self):
        before = {'benchmark': 'crc16', 'status': 'PASS', 'source_sha256': 'same',
                  'harness_bytes': 109, 'code_bytes': 100, 'instructions': 1000,
                  'assembly': {'crc16.s': 'ldd #1\n; <script>\nrts'}}
        old = {'compiler': 'CMOC', 'suite': 'kr16', 'flags': '-O2', 'version': 'CMOC 0.1.99', 'rows': [before]}
        new = dict(old, version='CMOC 0.1.101', rows=[dict(before, code_bytes=102, assembly={'crc16.s': 'ldd #2\n; <script>\nrts'})])
        cells = cmoc_version_comparison([new], [old])[0]
        self.assertEqual(cells[0].url, cmoc_diff_url('crc16', True))
        with tempfile.TemporaryDirectory() as directory:
            publish_cmoc_diffs([new], [old], directory)
            page = (Path(directory) / cells[0].url).read_text()
            self.assertIn('CMOC 0.1.99', page)
            self.assertIn('CMOC 0.1.101', page)
            self.assertIn('<span class="diff_chg">', page)
            self.assertNotIn('<script>', page)
