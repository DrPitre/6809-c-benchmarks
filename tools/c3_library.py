"""Verify the canonical native C3 library used by benchmark reports."""
import hashlib
import json
from pathlib import Path


def library_metadata(c3base, expected_revision):
    c3base=Path(c3base)
    metadata=json.loads((c3base/'lwbackend/LIBC.json').read_text())
    pin=(c3base/'nitros9-c-libs.revision').read_text().strip()
    if pin!=expected_revision or metadata.get('revision')!=expected_revision:
        raise ValueError('C3 canonical library revision mismatch')
    if metadata.get('url')!='https://github.com/nitros9project/nitros9-c-libs.git':
        raise ValueError('Unexpected C3 library source')
    def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    if digest(c3base/'lwbackend/libc3.a')!=metadata['library_sha256']:
        raise ValueError('C3 archive does not match its canonical build manifest')
    for folder,name in [('prep','c3prep'),('comp','c3comp'),('optx','c3optx')]:
        if digest(c3base/'build/unix'/folder/name)!=metadata['compiler_stages'][name]:
            raise ValueError('C3 library was built with different compiler stages')
    return metadata
