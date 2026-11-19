"""Execute identical K&R-compatible kernels through a shared USIM harness."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from check import SEEDS, crc16, insertion_sort, mix16

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cmoc_adapter', ROOT / 'tools/run-cmoc.py')
cmoc_adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmoc_adapter)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', choices=('c3', 'cmoc'), required=True)
    parser.add_argument('--optimization', choices=('0', '2'), required=True)
    parser.add_argument('--json', type=Path, required=True)
    args = parser.parse_args()
    build = ROOT / ('build/kr16-' + args.compiler + '-O' + args.optimization)
    build.mkdir(parents=True, exist_ok=True)
    c3base = ROOT / 'build/sources/nitros9-languages/c3'
    toolchain = ROOT / 'build/toolchain'
    env = os.environ.copy()
    env['C3BASE'] = str(c3base)
    env['C3LW_HOME'] = str(c3base / 'lwbackend')
    env['PATH'] = os.pathsep.join(str(c3base / 'build/unix' / stage)
                                 for stage in ('exec', 'prep', 'comp', 'optx')) + os.pathsep + str(c3base / 'lwbackend') + os.pathsep + str(toolchain / 'bin') + os.pathsep + env['PATH']
    report = {'compiler': args.compiler.upper(), 'suite': 'kr16',
              'target': '6809 / USIM bare-metal', 'kind': 'runtime',
              'flags': ('optimizer ' + ('off' if args.optimization == '0' else 'on')) if args.compiler == 'c3' else '-O' + args.optimization,
              'revision': env.get('GITHUB_SHA', 'local'), 'rows': [], 'commands': [],
              'emulator': 'USIM bundled with CMOC 0.1.99', 'cycles': None}
    (build / 'commands.log').write_text('')

    def run(command):
        report['commands'].append(command)
        result = subprocess.run(command, cwd=build, env=env, capture_output=True,
                                text=True, timeout=60)
        with (build / 'commands.log').open('a') as log:
            log.write(json.dumps(command) + '\n' + result.stdout + result.stderr)
        result.check_returncode()
        return result.stdout

    try:
        if args.compiler == 'c3':
            revision = (ROOT / 'tools/c3-revision.txt').read_text().strip()
            actual = run(['git', '-C', str(c3base), 'rev-parse', 'HEAD']).strip()
            if actual != revision:
                raise ValueError('C3 revision mismatch')
            report['toolchain_revision'] = revision
            report['version'] = 'C3 ' + revision[:12]
            libraries = ['-L' + str(c3base / 'lwbackend'), '-lc3lw']
        else:
            report['version'] = run(['cmoc', '--version']).strip()
            libraries = ['-L' + str(toolchain / 'share/cmoc/lib'), '-lcmoc-std-usim', '-lcmoc-crt-usim']
        report['assembler_version'] = run(['lwasm', '--version']).strip()
        report['linker_version'] = run(['lwlink', '--version']).strip()
        harness = ['lwasm', '--format=obj', '-o', 'harness.o']
        if args.compiler == 'cmoc':
            harness.append('-DCMOC_ABI')
        run([*harness, str(ROOT / 'adapters/kr16-usim.asm')])
        for reference in (crc16, insertion_sort, mix16):
            name = reference.__name__
            row = {'benchmark': name, 'status': 'FAIL'}
            try:
                source = ROOT / 'benchmarks/kr16' / (name + '.c')
                shutil.copyfile(source, build / source.name)
                row['source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
                if args.compiler == 'c3':
                    # -a stops BEFORE optimization, and writes beside the source.
                    run(['c3', name + '.c', '-a'])
                    assembly = name + '.a'
                    if args.optimization == '2':
                        run(['c3optx', assembly, name + '.opt.a'])
                        assembly = name + '.opt.a'
                    run(['c3-as', assembly, '-o=' + name + '.o'])
                else:
                    run(['cmoc', '--usim', '-O' + args.optimization, '-i', '-c', '-o', name + '.o', name + '.c'])
                run(['lwlink', '--format=srec', '--script=' + str(ROOT / 'adapters/kr16-usim.link'),
                     '--map=' + name + '.map', '-o', name + '.srec', 'harness.o', name + '.o', *libraries])
                output = run(['usim', name + '.srec'])
                actual = [tuple(int(word, 16) for word in line.split()) for line in output.splitlines()]
                expected = [(seed, reference(seed)) for seed in SEEDS]
                row.update(status='PASS' if actual == expected else 'FAIL', output=output, expected=expected,
                           loaded_bytes=cmoc_adapter.loaded_bytes(build / (name + '.srec')))
                maptext = (build / (name + '.map')).read_text()
                sections = re.findall(r'^Section: code \(' + re.escape(name) + r'\.o\) load at [0-9A-Fa-f]+, length ([0-9A-Fa-f]+)$', maptext, re.M)
                if len(sections) != 1:
                    raise ValueError('Expected one kernel code section')
                row['kernel_code_bytes'] = int(sections[0], 16)
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                row.update(status='FAIL', error=str(error))
            report['rows'].append(row)
            print(name, row['status'])
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
        print('Infrastructure error:', error)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if len(report['rows']) == 3 and all(r['status'] == 'PASS' for r in report['rows']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
