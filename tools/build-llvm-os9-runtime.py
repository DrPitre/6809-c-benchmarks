"""Rebuild the pinned default 6809 OS-9 C library with the RC2 compiler."""
import argparse
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--fast-bufio', action='store_true', help='Build the optional fast-I/O regression variant')
    args = parser.parse_args()
    pin = json.loads((ROOT / 'tools/llvm-os9-runtime.json').read_text())
    prefix = ROOT / 'build/llvm'
    source = ROOT / 'build/sources/picolibc'
    build = ROOT / 'build/picolibc-os9-runtime'
    env = os.environ.copy()
    env['PATH'] = str(prefix / 'bin') + os.pathsep + env['PATH']
    env.update(MC6809_TOOLCHAIN=str(prefix), LLVM_BIN=str(prefix / 'bin'))

    def run(command, cwd=ROOT):
        subprocess.run([str(v) for v in command], cwd=cwd, env=env, check=True)

    if not source.exists():
        source.mkdir(parents=True)
        run(['git', 'init', source])
        run(['git', '-C', source, 'remote', 'add', 'origin', pin['url']])
        run(['git', '-C', source, 'fetch', '--depth', '1', 'origin', pin['revision']])
        run(['git', '-C', source, 'checkout', '--detach', 'FETCH_HEAD'])
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'], text=True)
    if revision != pin['revision'] or dirty:
        raise SystemExit('picolibc checkout must match the clean pinned revision')
    version = (prefix / 'VERSION').read_text().strip()
    if '1.1.0-rc2' not in version:
        raise SystemExit('This runtime overlay requires the pinned LLVM RC2 release')

    # Keep the build tool local; do not alter the host Python installation.
    modules = ROOT / 'build/meson-python'
    env['PYTHONPATH'] = str(modules) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    available = subprocess.run(['python3', '-m', 'mesonbuild.mesonmain', '--version'], env=env,
                               capture_output=True, text=True)
    if available.returncode or available.stdout.strip() != pin['meson_version']:
        run(['python3', '-m', 'pip', 'install', '--disable-pip-version-check', '--upgrade',
             '--no-deps', '--target', modules, 'meson==' + pin['meson_version']])
    run(['sh', source / 'scripts/gen-mc6809-cross.sh'])
    # Ninja does not track changes to the compiler itself: always start fresh.
    if build.exists():
        shutil.rmtree(build)
    sysroot = prefix / 'lib/clang-runtimes/mc6809-unknown-os9'
    options = ['-Dmultilib=false', '-Dpicocrt=false', '-Dsemihost=false', '-Dos-os9=true',
               '-Dposix-console=true', '-Dtests=false', '-Doptimization=s',
               '-Dformat-default=integer', '-Dprintf-aliases=false', '-Dstdio-float=false',
               '-Dposix-extensions=false', '-Dsearch-extensions=true', '-Dwant-libm=false',
               '-Dmb-capable=false', '-Dio-long-long=false',
               '-Dfast-bufio=' + ('true' if args.fast_bufio else 'false')]
    run(['python3', '-m', 'mesonbuild.mesonmain', 'setup', build, source,
         '--cross-file', source / 'scripts/cross-clang-mc6809-unknown-os9.txt',
         '--prefix=' + str(sysroot), '--libdir=lib', '--includedir=include', *options])
    run(['python3', '-m', 'mesonbuild.mesonmain', 'install', '-C', build, '--quiet'])
    library = sysroot / 'lib/libc.a'
    selected = Path(subprocess.check_output([str(prefix / 'bin/mc6809-os9-clang'),
                                           '-print-file-name=libc.a'], text=True).strip())
    if selected.resolve() != library.resolve():
        raise SystemExit('Clang is not selecting the rebuilt OS-9 C library')
    metadata = {**pin, 'compiler_version': version, 'variant': 'mc6809 OS-9 integer',
                'fast_bufio': args.fast_bufio, 'options': options, 'libc_sha256': digest(library),
                'probe_source_sha256': digest(source / 'test/test-stdio/test-os9-text.c')}
    (prefix / 'OS9-RUNTIME.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Installed OS-9 text runtime fix from picolibc ' + revision[:12], flush=True)


if __name__ == '__main__':
    main()
