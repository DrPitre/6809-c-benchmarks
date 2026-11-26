import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from app_report import render_applications
from focused_report import render_focused
from matrix import render


class ApplicationReportTests(unittest.TestCase):
    def test_failed_execution_cannot_publish_size_or_pollute_kernel_report(self):
        report = {'suite': 'os9-apps', 'sources': {}, 'rows': [
            {'application': 'uniq', 'configuration': 'Test FAIL', 'status': 'FAIL',
             'module_bytes': 987654, 'requested_data_bytes': 876543,
             'cases': [{'status': 'FAIL'}]},
            {'application': 'uniq', 'configuration': 'Test PASS', 'status': 'PASS',
             'module_bytes': 12345, 'requested_data_bytes': 23456,
             'cases': [{'status': 'PASS'}]}]}
        page = render_applications([report])
        self.assertIn('1/2 application fixtures passed', page)
        self.assertIn('12345', page)
        self.assertNotIn('987654', page)
        self.assertNotIn('876543', page)
        self.assertIn('applications.html', render_focused([report])[1])
        self.assertEqual(render([report]), render([]))

    def test_runtime_fix_and_regression_are_identified_separately(self):
        report = {'suite': 'os9-apps', 'sources': {}, 'rows': [],
                  'llvm_runtime': {'url': 'https://github.com/markrvmurray/picolibc.git',
                                   'revision': 'abcdef123456' + '0' * 28},
                  'runtime_probe': {'status': 'FAIL'}}
        page = render_applications([report])
        self.assertIn('picolibc abcdef123456', page)
        self.assertIn('runtime regression: <strong>FAIL</strong>', page)
        self.assertNotIn('currently treats CR-delimited input as one line', page)

    def test_fixture_and_patch_links_use_the_run_revision(self):
        report = {'suite': 'os9-apps', 'sources': {}, 'rows': [], 'revision': 'a' * 40,
                  'vbcc_os9_runtime': {'patch_sha256': 'b' * 64}}
        page = render_applications([report])
        self.assertIn('/blob/' + 'a' * 40 + '/benchmarks/os9-apps/cases.json', page)
        self.assertIn('/blob/' + 'a' * 40 + '/tools/vbcc-os9-rw.patch', page)
        self.assertNotIn('/blob/main/', page)
