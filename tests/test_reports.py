import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
from matrix import render, validate_shared_sources
spec = importlib.util.spec_from_file_location('run_cmoc', TOOLS / 'run-cmoc.py')
cmoc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmoc)


class ReportTests(unittest.TestCase):
    def measure(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.srec'
            path.write_text(text)
            return cmoc.loaded_bytes(path)

    def test_srec_excludes_container_overhead(self):
        self.assertEqual(self.measure('S10528000102CF\nS9032800D4\n'), 2)

    def test_srec_rejects_bad_checksum_and_overlap(self):
        for text in ('S10528000102CE\n', 'S10528000102CF\nS10528000102CF\n'):
            with self.assertRaises(ValueError):
                self.measure(text)

    def test_failed_results_do_not_publish_sizes(self):
        report = {'compiler': '<CMOC>', 'target': '6809 / USIM', 'flags': '-O2',
                  'revision': 'abc', 'rows': [{'benchmark': 'crc16', 'status': 'FAIL',
                                             'kernel_code_bytes': 999, 'loaded_bytes': 1234}]}
        markdown, document = render([report])
        self.assertIn('Excluded (FAIL)', markdown)
        self.assertNotIn('999', document)
        self.assertIn('&lt;CMOC&gt;', document)
        self.assertIn('NOT RUN', document)


    def test_c3_compatibility_is_separate_from_correctness_and_sizes(self):
        report = {'compiler': 'C3', 'version': 'C3 test', 'target': '6809 / OS-9',
                  'kind': 'compile-compatibility', 'flags': 'optimizer on',
                  'revision': 'abc', 'smoke_link': 'PASS (not executed)',
                  'rows': [{'benchmark': 'crc16', 'status': 'COMPILE FAIL'}],
                  'probes': [{'name': 'unsigned_short', 'status': 'REJECTED'}]}
        markdown, document = render([report])
        host = markdown.split('## Host correctness')[1].split('## C3 compile')[0]
        sizes = markdown.split('## 6809 sizes (bytes)')[1].split('## C3 compile')[0]
        self.assertNotIn('C3 test', host)
        self.assertNotIn('C3 test', sizes)
        self.assertIn('COMPILE FAIL', document)
        self.assertIn('REJECTED', document)


    def test_shared_source_mismatch_blocks_comparison(self):
        reports = [{'suite': 'kr16', 'rows': [{'benchmark': 'crc16', 'status': 'PASS',
                                             'source_sha256': digest}]} for digest in ('aaa', 'bbb')]
        with self.assertRaises(ValueError):
            validate_shared_sources(reports)


if __name__ == '__main__':
    unittest.main()
