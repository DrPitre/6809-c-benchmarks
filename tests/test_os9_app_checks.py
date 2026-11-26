import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('os9_apps', ROOT / 'tools/run-os9-apps.py')
apps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apps)


class KnownCompilerFailureTests(unittest.TestCase):
    def setUp(self):
        fixtures = json.loads((ROOT / 'benchmarks/os9-apps/cases.json').read_text())
        self.row = {'application': 'ed', 'configuration_id': 'vb02', 'stage': 'execution',
                    'status': 'FAIL', 'cases': [{'id': c['id'], 'status': 'PASS', 'files': []}
                                               for c in fixtures if c['app'] == 'ed']}
        for case in self.row['cases']:
            if case['id'] == 'substitute':
                case.update(status='FAIL', actual='?\nalpha alpha\nbeta\n')
            elif case['id'] == 'save-reopen':
                case.update(status='FAIL', actual='?\nalpha\nbeta\n',
                            files=[{'id': 'RESULT', 'status': 'FAIL', 'actual': 'alpha\rbeta\r'}])

    def test_recognizes_only_the_recorded_bug_without_marking_it_pass(self):
        self.assertTrue(apps.known_vbcc_ed_offset_failure(self.row))
        self.assertEqual(self.row['status'], 'FAIL')
        other = copy.deepcopy(self.row)
        other['configuration_id'] = 'll02'
        self.assertFalse(apps.known_vbcc_ed_offset_failure(other))

    def test_different_output_or_saved_bytes_are_new_failures(self):
        for index in (0, 1):
            row = copy.deepcopy(self.row)
            failed = [c for c in row['cases'] if c['status'] == 'FAIL']
            if index == 0:
                failed[0]['actual'] = 'corrupted output'
            else:
                failed[1]['files'][0]['actual'] = 'alpha\nbeta\n'
            self.assertFalse(apps.known_vbcc_ed_offset_failure(row))

    def test_another_fixture_failure_or_failed_build_is_not_allowed(self):
        row = copy.deepcopy(self.row)
        row['cases'][0]['status'] = 'FAIL'
        self.assertFalse(apps.known_vbcc_ed_offset_failure(row))
        self.row['stage'] = 'build'
        self.assertFalse(apps.known_vbcc_ed_offset_failure(self.row))
