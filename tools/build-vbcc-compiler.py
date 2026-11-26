"""Build the pinned preview compiler with the array-offset boundary fix."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA256 = 'e1e80894c972bc38a1fe2804fe4bce8559e4be6e53e4c878de6f459a6929637e'
SOURCE_SHA256 = '3efdd0064263dfdb68a53edf6abf45ed546b272451c3107db2106ab304005b91'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    archive = ROOT / 'build/sources/vbcc6809/vbcc.tar.gz'
    if digest(archive) != ARCHIVE_SHA256:
        raise SystemExit('vbcc source archive checksum mismatch')
    build = ROOT / 'build/vbcc-compiler'
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)
    with tarfile.open(archive, 'r:gz') as tar:
        # This historical archive contains several self-referencing hardlinks
        # in unrelated targets. Skip those invalid entries explicitly.
        members = [m for m in tar.getmembers() if not (m.islnk() and m.name == m.linkname)]
        tar.extractall(build, members=members)
    source = build / 'vbcc'
    if digest(source / 'type_expr.c') != SOURCE_SHA256:
        raise SystemExit('vbcc type-expression source checksum mismatch')
    patch = ROOT / 'patches/vbcc-array-offset/fix.patch'
    commands = []
    cc = 'cc -std=c99 -O2 -Wno-format-security -Wno-error=implicit-function-declaration -Wno-error=int-conversion'
    log = ROOT / 'build/vbcc-compiler-build.log'
    def run(command, input=None):
        commands.append(command)
        with log.open('ab') as output:
            result = subprocess.run(command, cwd=source, input=input, stdout=output,
                                    stderr=subprocess.STDOUT, timeout=180)
        if result.returncode:
            print(log.read_text(errors='replace')[-6000:])
            result.check_returncode()
    log.write_text('')
    run(['patch', '--batch', '-p1', '-i', str(patch)])
    run(['make', 'TARGET=hc12', 'CC=' + cc, 'bin/dtgen'])
    (source / 'objects/hc12').mkdir(parents=True, exist_ok=True)
    # Select dtgen's host-detected defaults. Generate once before parallel make
    # because the upstream dt.h/dt.c recipes otherwise race each other.
    run(['bin/dtgen', 'machines/hc12/machine.dt', 'objects/hc12/dt.h',
         'objects/hc12/dt.c'], input=b'\n' * 256)
    run(['make', '-j2', 'TARGET=hc12', 'CC=' + cc, 'bin/vbcchc12'])
    target = ROOT / 'build/vbcc/bin/vbcchc12'
    shutil.copy2(source / 'bin/vbcchc12', target)
    metadata = {'source_archive_sha256': ARCHIVE_SHA256, 'original_source_sha256': SOURCE_SHA256,
                'patch_sha256': digest(patch), 'patched_source_sha256': digest(source / 'type_expr.c'),
                'compiler_sha256': digest(target), 'commands': commands,
                'description': 'Preview 2026-01-25 + one-past array-offset boundary fix'}
    (ROOT / 'build/vbcc/COMPILER-PATCH.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Installed source-built vbcc with one-past array-offset fix', flush=True)


if __name__ == '__main__':
    main()
