import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
from matrix import render, validate_shared_sources, source_link
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

    def test_four_compiler_gap_uses_next_smallest_and_requires_valid_results(self):
        reports = []
        for compiler, size in (("C3", 467), ("CMOC", 374), ("LLVM", 430), ("VBCC", 480)):
            reports.append({"compiler": compiler, "suite": "kr16", "kind": "runtime",
                            "target": "6809 / USIM bare-metal", "revision": "abc",
                            "flags": "optimizer on" if compiler == "C3" else "-O2",
                            "rows": [{"benchmark": "crc16", "status": "PASS",
                                      "source_sha256": "same", "loaded_bytes": size,
                                      "kernel_code_bytes": size}]})
        markdown, _ = render(reports)
        self.assertIn("| On | 467 | 374 | 430 | 480 | CMOC by 56 B |", markdown)
        reports[-1]["rows"][0]["status"] = "FAIL"
        markdown, _ = render(reports)
        self.assertIn("| On | 467 | 374 | 430 | Excluded (FAIL) | — |", markdown)

    def test_source_links_pin_report_revision(self):
        revision = 'a' * 40
        link = source_link('Function calls', 'benchmarks/kr16/calls16.c', revision)
        self.assertEqual(link.url, 'https://github.com/DrPitre/6809-c-benchmarks/blob/' + revision + '/benchmarks/kr16/calls16.c')
        report = {'compiler': 'C3', 'suite': 'kr16', 'kind': 'runtime',
                  'target': '6809 / USIM bare-metal', 'revision': revision,
                  'flags': 'optimizer on', 'rows': [{'benchmark': 'calls16', 'status': 'PASS', 'source_sha256': 'b' * 64}]}
        markdown, document = render([report])
        self.assertIn('/blob/' + revision + '/benchmarks/kr16/support/step3.c', document)
        self.assertIn('[calls16.c](' + link.url + ')', markdown)
        # Each comparison table has one linked name spanning both settings.
        for title in ('Benchmark code size', 'Complete test program size', 'Shared-suite correctness'):
            section = document.split('<h2>' + title + '</h2>')[1].split('</table>')[0]
            self.assertEqual(section.count('href="' + link.url + '"'), 1)
            self.assertIn('rowspan="2" scope="rowgroup"', section)
        self.assertIn('|  | Off |', markdown)


if __name__ == '__main__':
    unittest.main()
