import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('os9_apps', ROOT / 'tools/run-os9-apps.py')
apps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apps)


class ApplicationChecksTests(unittest.TestCase):
    def setUp(self):
        self.report = {'reached_completion': True, 'runtime_probe': {'status': 'PASS'},
                       'vbcc_pointer_probes': [{'configuration_id': c, 'status': 'PASS'} for c in ('vb00', 'vb02')],
                       'rows': [{'status': 'PASS'}, {'status': 'PASS'}]}

    def test_requires_complete_rows_and_both_pointer_regressions(self):
        self.assertTrue(apps.report_passes(self.report, 2))
        self.assertFalse(apps.report_passes(self.report, 3))
        self.report['vbcc_pointer_probes'].pop()
        self.assertFalse(apps.report_passes(self.report, 2))

    def test_previously_known_ed_failure_is_no_longer_accepted(self):
        self.report['rows'][0].update(status='FAIL', known_failure='old vbcc offset bug')
        self.assertFalse(apps.report_passes(self.report, 2))

    def test_runtime_and_process_failures_are_not_accepted(self):
        for field in ('runtime_probe', 'vbcc_pointer_probes'):
            report = copy.deepcopy(self.report)
            target = report[field] if field == 'runtime_probe' else report[field][0]
            target['status'] = 'FAIL'
            self.assertFalse(apps.report_passes(report, 2))
        self.report['reached_completion'] = False
        self.assertFalse(apps.report_passes(self.report, 2))

    def test_duplicate_configuration_cannot_replace_a_missing_regression(self):
        self.report['vbcc_pointer_probes'][1]['configuration_id'] = 'vb00'
        self.assertFalse(apps.report_passes(self.report, 2))
