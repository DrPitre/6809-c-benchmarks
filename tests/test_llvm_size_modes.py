import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from assembly_report import assembly_url, publish_assembly, size_assembly_url
from matrix import render


def report(compiler, flags, size):
    return {'compiler': compiler, 'flags': flags, 'suite': 'kr16',
            'target': '6809 / USIM bare-metal', 'revision': 'a' * 40,
            'rows': [{'benchmark': 'crc16', 'status': 'PASS', 'source_sha256': 'same',
                      'code_bytes': size, 'loaded_bytes': size + 100, 'instructions': size * 10,
                      'assembly': {'crc16.s': compiler + ' ' + flags + ' assembly'},
                      'linker_map': compiler + ' ' + flags + ' map'}]}


class LLVMSizeModeTests(unittest.TestCase):
    def setUp(self):
        self.baseline = [report('LLVM', '-O0', 140), report('LLVM', '-O2', 280),
                         report('VBCC', '-O2', 92)]
        self.extra = [report('LLVM', '-Os', 72), report('LLVM', '-Oz', 81)]

    def test_size_modes_do_not_replace_on_off_results_or_assembly(self):
        reports = self.baseline + self.extra
        for order in (reports, list(reversed(reports))):
            markdown, document = render(order)
            self.assertIn('LLVM size optimization versus vbcc', document)
            for label in ('LLVM -O2', 'LLVM -Os', 'LLVM -Oz', 'VBCC -O2'):
                self.assertIn(label, document)
            self.assertIn('[280](' + assembly_url(self.baseline[1], self.baseline[1]['rows'][0]) + ')', markdown)
            self.assertIn('[140](' + assembly_url(self.baseline[0], self.baseline[0]['rows'][0]) + ')', markdown)
            with tempfile.TemporaryDirectory() as directory:
                publish_assembly(order, directory)
                urls = [assembly_url(r, r['rows'][0]) for r in reports]
                self.assertEqual(len(set(urls)), 3)  # on, off, size-comparison
                size_page = (Path(directory) / size_assembly_url('crc16')).read_text()
                for r in (self.baseline[1], self.baseline[2], *self.extra):
                    self.assertIn(r['rows'][0]['assembly']['crc16.s'], size_page)
                for r in self.baseline[:2]:
                    page = (Path(directory) / assembly_url(r, r['rows'][0])).read_text()
                    self.assertIn(r['rows'][0]['assembly']['crc16.s'], page)
                    self.assertNotIn('LLVM -Os assembly', page)

    def test_failed_size_result_has_no_numeric_link_or_rank(self):
        reports = copy.deepcopy(self.baseline + self.extra)
        reports[-1]['rows'][0]['status'] = 'FAIL'
        markdown, document = render(reports)
        self.assertIn('Excluded (FAIL)', document)
        self.assertNotIn('[81](', markdown)
        self.assertIn('0/12 tests included in this ranking', markdown)

    def test_historical_reports_do_not_gain_size_modes(self):
        self.assertNotIn('LLVM size optimization versus vbcc', render(self.baseline)[1])
        self.assertNotEqual(assembly_url(self.baseline[0], self.baseline[0]['rows'][0]),
                            size_assembly_url('crc16'))
