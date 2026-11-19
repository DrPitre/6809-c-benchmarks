import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from execution_metrics import boundary_address, instruction_counts


class ExecutionMetricsTests(unittest.TestCase):
    def test_boundaries_in_three_linker_formats(self):
        maps = ['Symbol: bench_begin (harness.o) = 2835',
                '    2835 2835 0 1     bench_begin',
                '  0x2835 bench_begin: global reloc, size 0']
        for text in maps:
            self.assertEqual(boundary_address(text, 'bench_begin'), 0x2835)
        with self.assertRaises(ValueError):
            boundary_address('', 'bench_begin')
        with self.assertRaises(ValueError):
            boundary_address(maps[0] + '\n' + maps[0], 'bench_begin')

    def test_counts_require_every_seed_and_preserve_order(self):
        self.assertEqual(instruction_counts('BENCH_INSTRUCTIONS 11\nBENCH_INSTRUCTIONS 20\n', [0, 65535]),
                         [{'seed': 0, 'instructions': 11}, {'seed': 65535, 'instructions': 20}])
        for text in ('', 'BENCH_INSTRUCTIONS 0\n', 'BENCH_INSTRUCTIONS 11\nBENCH_INSTRUCTIONS 20\n'):
            with self.assertRaises(ValueError):
                instruction_counts(text, [0])
