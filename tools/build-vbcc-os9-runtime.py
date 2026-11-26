"""Assemble an OS-9 I/O override from the checksum-pinned vbcc preview."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    work = ROOT / 'build/vbcc-os9-runtime'
    work.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'build/sources/vbcc6809/libsrc/6809-os9/rw.s'
    if digest(source) != '7859349154591f4cd698af5ce7daddb638596769328d26e55d8f72006e6cd4f6':
        raise SystemExit('vbcc OS-9 read-wrapper source checksum mismatch')
    patch = ROOT / 'tools/vbcc-os9-rw.patch'
    target = ROOT / 'build/vbcc/targets/6809-os9'
    shutil.copyfile(source, work / 'rw.s')
    subprocess.run(['patch', '--batch', '-p1', '-i', str(patch)], cwd=work, check=True)
    output = target / 'lib/bench-rw.o'
    subprocess.run([str(ROOT / 'build/vbcc/bin/vasm6809_std'), '-quiet', '-Fvobj',
                    '-I' + str(target / 'include'), str(work / 'rw.s'), '-o', str(output)], check=True)
    metadata = {'source_archive_sha256': '18db043d4d4c8b0a16d4fa4b813616f277fcfb3667be0eda2334a8b8b024917e',
                'source_sha256': digest(source), 'patch_sha256': digest(patch),
                'object_sha256': digest(output)}
    (ROOT / 'build/vbcc/OS9-RUNTIME.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    main()
