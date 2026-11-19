import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from assembly_report import assembly_url, publish_assembly
from matrix import render


class AssemblyReportTests(unittest.TestCase):
    def test_links_publish_exact_assembly_and_support_files_safely(self):
        row = {'benchmark': 'calls16', 'status': 'PASS', 'source_sha256': 'same',
               'kernel_code_bytes': 100, 'loaded_bytes': 200,
               'assembly': {'calls16.s': 'lda #1 ; <script>', 'step3.s': 'rts'},
               'linker_map': 'calls16.o .text 100'}
        report = {'compiler': 'CMOC', 'suite': 'kr16', 'flags': '-O2',
                  'target': '6809 / USIM bare-metal', 'revision': 'a' * 40, 'rows': [row]}
        url = assembly_url(report, row)
        markdown, document = render([report])
        self.assertIn('[100](' + url + ')', markdown)
        self.assertIn('href="' + url + '">200</a>', document)
        self.assertIn('class="number"><a', document)
        self.assertNotEqual(url, assembly_url(dict(report, flags='-O0'), row))
        with tempfile.TemporaryDirectory() as directory:
            publish_assembly([report], directory)
            page = (Path(directory) / url).read_text()
            self.assertIn('step3.s', page)
            self.assertIn('lda #1 ; &lt;script&gt;', page)
            self.assertIn('calls16.o .text 100', page)
            self.assertIn('a' * 40, page)
        row['status'] = 'FAIL'
        markdown, _ = render([report])
        self.assertNotIn('[100](', markdown)
