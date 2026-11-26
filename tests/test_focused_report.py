import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from focused_report import configurations, render_focused, summarize


def sample(compiler, flags, sizes, instructions):
    return {'compiler': compiler, 'suite': 'kr16', 'flags': flags, 'version': compiler + ' test',
            'revision': 'a' * 40, 'run_started_at': '2026-11-26T13:16:07Z',
            'workflow_run_url': 'https://github.com/DrPitre/6809-c-benchmarks/actions/runs/123',
            'rows': [{'benchmark': name, 'status': 'PASS', 'code_bytes': size,
                      'instructions': count, 'assembly': {name + '.s': 'rts'}}
                     for name, size, count in zip(('crc16', 'mix16'), sizes, instructions)]}


class FocusedReportTests(unittest.TestCase):
    def setUp(self):
        self.reports = [sample('VBCC', '-O2', [10, 40], [100, 100]),
                        sample('LLVM', '-O2', [20, 20], [50, 50]),
                        sample('LLVM', '-Os', [15, 30], [75, 75]),
                        sample('LLVM', '-Oz', [30, 40], [90, 90]),
                        sample('VBCC', '-O0', [30, 60], [200, 200])]

    def test_normalization_frontier_and_unoptimized_separation(self):
        configs = configurations(self.reports)
        self.assertEqual(len(configs), 4)
        summaries, eligible = summarize(configs)
        self.assertEqual(eligible, ['crc16', 'mix16'])
        by_label = {c['label']: c for c in summaries}
        # Equal size geometric means: 10*40 == 20*20, despite different totals.
        self.assertAlmostEqual(by_label['VBCC -O2']['code_bytes_index'], 100)
        self.assertAlmostEqual(by_label['LLVM -O2']['code_bytes_index'], 100)
        self.assertAlmostEqual(by_label['LLVM -O2']['instructions_index'], 100)
        self.assertAlmostEqual(by_label['VBCC -O2']['instructions_index'], 200)
        self.assertTrue(by_label['LLVM -O2']['frontier'])
        self.assertFalse(by_label['VBCC -O2']['frontier'])
        self.assertFalse(by_label['LLVM -Oz']['frontier'])
        self.assertEqual(len(configurations(self.reports, optimized=False)), 1)

    def test_common_eligibility_excludes_failed_test_from_every_score(self):
        reports = copy.deepcopy(self.reports)
        reports[0]['rows'][0].update(status='FAIL', code_bytes=999999)
        summaries, eligible = summarize(configurations(reports))
        self.assertEqual(eligible, ['mix16'])
        self.assertEqual({s['code_bytes'] for s in summaries}, {20, 30, 40})
        markdown, document = render_focused(reports)
        self.assertIn('Excluded (FAIL)', document)
        self.assertIn('Excluded from every index: CRC16', document)
        self.assertNotIn('999,999', document)
        self.assertIn('Some results failed', document)

    def test_focused_page_defaults_and_details_links(self):
        markdown, document = render_focused(self.reports, [('llvm-1.0', 'LLVM 1.0')], True)
        self.assertIn('id="size" role="tabpanel" aria-labelledby="tab-size" tabindex="0"><h2>', document)
        self.assertIn('id="instructions" role="tabpanel" aria-labelledby="tab-instructions" tabindex="0" hidden', document)
        self.assertEqual(document.count('role="tab"'), 3)
        self.assertIn('November 26, 2026 at 8:16 AM EST', document)
        self.assertIn('Instruction counts are not cycle timing', document)
        self.assertIn('href="details.html"', document)
        self.assertIn('href="history/llvm-1.0/index.html"', document)
        self.assertIn('details.html#cmoc-release-comparison', document)
        self.assertNotIn('<details open', document)
        self.assertNotIn('Original C89 compatibility diagnostics', document)
        self.assertIn('assembly/', document)
        self.assertIn('Raw results', markdown)

    def test_empty_and_missing_metrics_do_not_invent_rankings(self):
        summaries, eligible = summarize([])
        self.assertEqual((summaries, eligible), ([], []))
        reports = copy.deepcopy(self.reports)
        reports[0]['rows'][0].pop('instructions')
        self.assertEqual(summarize(configurations(reports))[1], ['mix16'])
        reports[0]['rows'][1]['status'] = 'FAIL'
        summaries, eligible = summarize(configurations(reports))
        self.assertFalse(eligible)
        self.assertTrue(all(s['code_bytes_index'] is None and not s['frontier'] for s in summaries))
