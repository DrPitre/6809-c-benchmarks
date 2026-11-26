"""Build the pinned non-floating-point CMOC OS-9 C library."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    pin = json.loads((ROOT / 'tools/os9-app-sources.json').read_text())['c_libs']
    source = ROOT / 'build/sources/nitros9-c-libs'
    env = os.environ.copy()
    env['PATH'] = str(ROOT / 'build/toolchain/bin') + os.pathsep + env['PATH']
    def run(command):
        return subprocess.check_output(command, env=env, text=True).strip()
    if not source.exists():
        source.mkdir(parents=True)
        run(['git', 'init', str(source)])
        run(['git', '-C', str(source), 'remote', 'add', 'origin', pin['url']])
        run(['git', '-C', str(source), 'fetch', '--depth', '1', 'origin', pin['revision']])
        run(['git', '-C', str(source), 'checkout', '--detach', 'FETCH_HEAD'])
    if run(['git', '-C', str(source), 'rev-parse', 'HEAD']) != pin['revision']:
        raise SystemExit('CMOC OS-9 library source revision mismatch')
    if run(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no']):
        raise SystemExit('CMOC OS-9 library source has local modifications')
    compiler = Path(shutil.which('cmoc', path=env['PATH']))
    version = run([str(compiler), '--version'])
    if version != 'cmoc (cmoc 0.1.101)':
        raise SystemExit('Unexpected CMOC version: ' + version)
    output = ROOT / 'build/cmoc-os9'
    output.mkdir(parents=True, exist_ok=True)
    flags = '--cpp="cpp -Wno-builtin-macro-redefined" --os9 -O2 -I' + str(source / 'include')
    commands = [['make', '-C', str(source / 'lib'), 'clean'],
                ['make', '-C', str(source / 'lib'), '-j2', 'libc.a', 'BASE_CFLAGS=' + flags]]
    with (output / 'build.log').open('w') as log:
        for command in commands:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    shutil.copy2(source / 'lib/libc.a', output / 'libc.a')
    metadata = {**pin, 'library': 'libc.a (non-floating-point)', 'library_sha256': digest(output / 'libc.a'),
                'compiler_version': version, 'compiler_sha256': digest(compiler),
                'library_cflags': flags, 'commands': commands}
    (output / 'LIBRARY.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Built pinned nitros9-c-libs/libc.a at ' + pin['revision'], flush=True)


if __name__ == '__main__':
    main()
