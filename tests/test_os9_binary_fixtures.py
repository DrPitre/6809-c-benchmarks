import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

apps = module('os9_apps_binary', 'tools/run-os9-apps.py')
rof = module('rof_fixtures', 'tools/make-os9-rof-fixtures.py')


class BinaryFixtureTests(unittest.TestCase):
    def test_binary_cr_lf_nul_and_high_bytes_are_never_text_converted(self):
        data = bytes(range(256))
        self.assertEqual(apps.fixture_bytes({'hex': data.hex()}), data)
        self.assertEqual(apps.fixture_bytes({'text': 'one\ntwo\n'}), b'one\rtwo\r')

    def test_committed_rof_archives_and_expected_files_match_generator(self):
        cases = json.loads((ROOT / 'benchmarks/os9-apps/cases.json').read_text())
        self.assertEqual([c for c in cases if c['app'] == 'lb'], rof.fixtures())
        for case in rof.fixtures():
            modules = [bytes.fromhex(v['hex']) for v in case['output_files'].values() if 'hex' in v]
            self.assertEqual(b''.join(modules), bytes.fromhex(case['input_hex']))
            self.assertTrue(case['isolated'])

    def test_rof_header_fields_and_reference_width_have_fixed_disk_sizes(self):
        raw = rof.module('t', code=b'\x0d\x0a', data=b'\xff', direct=b'\x00',
                         globals=[('g', 4, 1)], locals=[(0x20, 1)])
        self.assertEqual(raw[:4], bytes.fromhex('62cd2387'))
        self.assertEqual(raw[18:24], bytes.fromhex('000100010002'))
        self.assertEqual(raw[28:30], b't\x00')
        self.assertEqual(raw[-5:], bytes.fromhex('0001200001'))
