import hashlib
import json
from pathlib import Path
import sys
import unittest
import tempfile
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from matrix import cmoc_version_comparison, render
from assembly_report import publish_cmoc_diffs, cmoc_diff_url


class HistoryTests(unittest.TestCase):
    def test_simulator_provenance_does_not_relabel_historical_reports(self):
        root = Path(__file__).resolve().parents[1]
        historical = json.loads((root / 'history/llvm-1.0/results.json').read_text())
        _, archived = render(historical, historical=True)
        self.assertIn('USIM is bundled with CMOC 0.1.99', archived)
        self.assertNotIn('Simulator provenance', archived)
        current = json.loads(json.dumps(historical))
        revision = '1' * 40
        adapter = '2' * 64
        for report in current:
            if report.get('suite') == 'kr16':
                report.update(emulator_revision=revision,
                              emulator_adapter_sha256=adapter,
                              emulator_source_url='https://github.com/markrvmurray/usim/tree/' + revision)
        markdown, document = render(current)
        for text in (markdown, document):
            self.assertIn('Simulator provenance', text)
            self.assertIn('https://github.com/markrvmurray/usim/tree/' + revision, text)
            self.assertIn(adapter, text)
            self.assertNotIn('USIM is bundled with CMOC 0.1.99', text)

    def test_llvm_snapshot_label_and_publication_preserve_both_histories(self):
        root = Path(__file__).resolve().parents[1]
        snapshot = root / 'history/llvm-1.0/results.json'
        metadata = json.loads(snapshot.with_name('snapshot.json').read_text())
        data = snapshot.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), metadata['results_sha256'])
        reports = json.loads(data)
        llvm = [r for r in reports if r.get('suite') == 'kr16' and r['compiler'] == 'LLVM']
        self.assertEqual(len(llvm), 2)
        self.assertTrue(all(r['release'] == 'RELEASE_1.0' for r in llvm))
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            inputs = base / 'reports'
            inputs.mkdir()
            # The CLI consumes one report object per input file.
            (inputs / 'all.json').write_text(json.dumps(reports[0]))
            output = base / 'site'
            subprocess.run([sys.executable, str(root / 'tools/matrix.py'),
                            str(inputs), str(output)], check=True, capture_output=True)
            self.assertIn('history/llvm-1.0/index.html', (output / 'index.html').read_text())
            for name in ('llvm-1.0', 'cmoc-0.1.99'):
                self.assertEqual((output / 'history' / name / 'results.json').read_bytes(),
                                 (root / 'history' / name / 'results.json').read_bytes())
            archived = (output / 'history/llvm-1.0/index.html').read_text()
            self.assertIn('Historical snapshot: LLVM-MC6809 1.0', archived)
            self.assertNotIn('Historical snapshot: CMOC 0.1.99', archived)

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
