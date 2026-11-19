import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from matrix import cmoc_version_comparison, render


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
        for changes in ({'source_sha256': 'different'}, {'status': 'FAIL'}, {'harness_bytes': 113}):
            new['rows'] = [dict(old['rows'][0], **changes)]
            cells = cmoc_version_comparison([new], [old])[0]
            self.assertEqual(cells[2], 'Not comparable')
            self.assertEqual(cells[3], 'Not comparable')
