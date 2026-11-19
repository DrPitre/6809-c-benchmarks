"""Probe unchanged C89 kernels with C3; compilation is not runtime correctness."""
import argparse
import json
import os
import shutil
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ('crc16', 'insertion_sort', 'mix16')
PROBES = {
    'kr_function': 'unsigned probe(seed) unsigned seed; { return seed; }\n',
    'typed_parameters': 'unsigned probe(unsigned seed) { return seed; }\n',
    'unsigned_short': 'unsigned short value;\n',
    'unsigned_long': 'unsigned long value;\n',
    'unsigned_suffix': 'unsigned probe() { return 1U; }\n',
    'limits_header': '#include <limits.h>\nint probe() { return 0; }\n',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--optimizer', choices=('on', 'off'), default='on')
    parser.add_argument('--json', type=Path, required=True)
    args = parser.parse_args()
    c3base = ROOT / 'build/sources/nitros9-languages/c3'
    build = ROOT / ('build/c3-' + args.optimizer)
    build.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['C3BASE'] = str(c3base)
    env['C3LW_HOME'] = str(c3base / 'lwbackend')
    env['PATH'] = os.pathsep.join(str(c3base / 'build/unix' / stage)
                                 for stage in ('exec', 'prep', 'comp', 'optx')) + os.pathsep + str(c3base / 'lwbackend') + os.pathsep + str(ROOT / 'build/toolchain/bin') + os.pathsep + env['PATH']
    revision = (ROOT / 'tools/c3-revision.txt').read_text().strip()
    flags = [] if args.optimizer == 'on' else ['-o']
    report = {'compiler': 'C3', 'version': 'C3 ' + revision[:12],
              'target': '6809 / OS-9', 'kind': 'compile-compatibility',
              'flags': 'optimizer ' + args.optimizer + (' (-o)' if flags else ' (default)'),
              'revision': env.get('GITHUB_SHA', 'local'), 'toolchain_revision': revision,
              'source_url': 'https://github.com/nitros9project/nitros9-languages/tree/' + revision + '/c3',
              'rows': [], 'probes': [], 'commands': [], 'runtime_status': 'NOT RUN'}

    def run(command, label):
        report['commands'].append(command)
        result = subprocess.run(command, cwd=build, env=env, capture_output=True,
                                text=True, timeout=60)
        output = result.stdout + result.stderr
        (build / (label + '.log')).write_text(output)
        return result.returncode, output

    infrastructure_ok = False
    try:
        actual = subprocess.check_output(['git', '-C', str(c3base), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != revision:
            raise ValueError('C3 checkout does not match pinned revision')
        # A known-supported program must link before kernel failures can be
        # classified as compatibility results instead of broken infrastructure.
        (build / 'smoke.c').write_text('int main() { return 0; }\n')
        module = build / 'smoke'
        module.unlink(missing_ok=True)
        code, output = run(['c3', 'smoke.c', *flags, '-f=smoke'], 'smoke')
        data = module.read_bytes() if module.exists() else b''
        if code != 0 or len(data) < 13 or data[:2] != b'\x87\xcd' or int.from_bytes(data[2:4], 'big') != len(data):
            raise ValueError('C3 smoke program did not link a valid-sized OS-9 module: ' + output)
        report['smoke_link'] = 'PASS (not executed)'
        for name, source in PROBES.items():
            (build / (name + '.c')).write_text(source)
            artifact = build / (name + '.r')
            artifact.unlink(missing_ok=True)
            code, output = run(['c3', name + '.c', *flags, '-r'], name)
            report['probes'].append({'name': name, 'status': 'ACCEPTED' if code == 0 and artifact.exists() else 'REJECTED', 'exit_code': code, 'diagnostics': output})
        for name in BENCHMARKS:
            artifact = build / (name + '.r')
            artifact.unlink(missing_ok=True)
            shutil.copyfile(ROOT / 'benchmarks' / (name + '.c'), build / (name + '.c'))
            code, output = run(['c3', name + '.c', *flags,
                                '-v=' + str(ROOT / 'include'), '-r'], name)
            status = 'COMPILED (NOT RUN)' if code == 0 and artifact.exists() else 'COMPILE FAIL'
            report['rows'].append({'benchmark': name, 'status': status, 'exit_code': code, 'diagnostics': output})
            print(name, status)
        infrastructure_ok = True
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
        print('C3 infrastructure error:', error)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if infrastructure_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
