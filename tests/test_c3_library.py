import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from c3_library import library_metadata


class CanonicalLibraryTests(unittest.TestCase):
    def test_rejects_stale_archive_compiler_and_mismatched_pin(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);(root/'lwbackend').mkdir()
            pin='a'*40
            (root/'nitros9-c-libs.revision').write_text(pin+'\n')
            archive=root/'lwbackend/libc3.a';archive.write_bytes(b'library')
            metadata={'url':'https://github.com/nitros9project/nitros9-c-libs.git','revision':pin,
                      'library_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'compiler_stages':{}}
            for folder,name in [('prep','c3prep'),('comp','c3comp'),('optx','c3optx')]:
                stage=root/'build/unix'/folder/name;stage.parent.mkdir(parents=True);stage.write_bytes(name.encode())
                metadata['compiler_stages'][name]=hashlib.sha256(stage.read_bytes()).hexdigest()
            (root/'lwbackend/LIBC.json').write_text(json.dumps(metadata))
            self.assertEqual(library_metadata(root,pin),metadata)
            with self.assertRaisesRegex(ValueError,'revision'):library_metadata(root,'b'*40)
            archive.write_bytes(b'stale')
            with self.assertRaisesRegex(ValueError,'archive'):library_metadata(root,pin)
            archive.write_bytes(b'library')
            (root/'build/unix/comp/c3comp').write_bytes(b'changed compiler')
            with self.assertRaisesRegex(ValueError,'compiler'):library_metadata(root,pin)
