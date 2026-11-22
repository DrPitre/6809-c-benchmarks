import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from assembly_report import assembly_url, comparison_compilers, publish_assembly
from execution_metrics import boundary_address, code_size_without_harness
from matrix import overall_sizes, render


class GCC6809ReportsTests(unittest.TestCase):
    def reports(self):
        return [dict(compiler=compiler, suite='kr16', flags='-O2', revision='local',
                     target='6809 / USIM bare-metal',
                     rows=[dict(benchmark='crc16', status='PASS', source_sha256='same',
                                code_bytes=size, loaded_bytes=size + 109,
                                assembly={'crc16.s': 'rts'})])
                for compiler, size in zip(('C3', 'CMOC', 'LLVM', 'VBCC', 'GCC6809'),
                                          (100, 110, 120, 130, 140))]

    def test_fifth_compiler_ranks_and_links_to_assembly(self):
        reports = self.reports()
        markdown, document = render(reports)
        self.assertIn('| C3 | CMOC | LLVM | VBCC | GCC6809 |', markdown)
        self.assertIn('rank rank-5', document)
        self.assertIn('5th place', document)
        compilers = comparison_compilers(reports)
        shared = {('crc16', True, r['compiler']): r['rows'][0] for r in reports}
        ranking, eligible = overall_sizes(shared, True, compilers)
        self.assertEqual(eligible, ['crc16'])
        self.assertEqual(ranking[-1][:2], ['5th', 'GCC6809'])
        with tempfile.TemporaryDirectory() as directory:
            publish_assembly(reports, directory)
            page = (Path(directory) / assembly_url(reports[-1], reports[-1]['rows'][0])).read_text()
            self.assertIn('>GCC6809<small>', page)
            self.assertIn('colspan="5"', page)

    def test_gcc_failure_excludes_common_ranking_and_old_reports_stay_four_columns(self):
        reports = self.reports()
        reports[-1]['rows'][0]['status'] = 'FAIL'
        _, document = render(reports)
        self.assertNotIn('class="rank rank-', document)
        self.assertIn('Excluded (FAIL)', document)
        self.assertEqual(comparison_compilers(reports[:-1]), ('C3', 'CMOC', 'LLVM', 'VBCC'))
        _, old_document = render(reports[:-1], historical=True)
        self.assertNotIn('GCC6809', old_document)

    def test_gnu_linker_boundaries_include_helpers_but_exclude_harness(self):
        maptext = '''
 .start 0x00002800 0x6d harness.o
                0x00002800                start
                0x0000282f                bench_begin
                0x00002832                bench_end
                0x0000286d                harness_end
 .text 0x0000286d 0x100 crc16.o
 .text 0x0000296d 0x22 libgcc.a(mulhi3.o)
'''
        self.assertEqual(boundary_address(maptext, 'bench_begin'), 0x282f)
        self.assertEqual(code_size_without_harness(maptext, 109 + 256 + 34), (290, 109))
        with self.assertRaises(ValueError):
            boundary_address(maptext + ' 0x00002830 bench_begin\n', 'bench_begin')
