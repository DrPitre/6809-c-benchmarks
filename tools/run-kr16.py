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

from execution_metrics import boundary_address, instruction_counts
from check import SEEDS
from shared_suite import REFERENCES, sources

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cmoc_adapter', ROOT / 'tools/run-cmoc.py')
cmoc_adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmoc_adapter)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', choices=('c3', 'cmoc', 'llvm', 'vbcc'), required=True)
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
    env['PATH'] = str(ROOT / 'build/vbcc/bin') + os.pathsep + str(ROOT / 'build/llvm/bin') + os.pathsep + os.pathsep.join(str(c3base / 'build/unix' / stage)
                                 for stage in ('exec', 'prep', 'comp', 'optx')) + os.pathsep + str(c3base / 'lwbackend') + os.pathsep + str(toolchain / 'bin') + os.pathsep + env['PATH']
    report = {'compiler': args.compiler.upper(), 'suite': 'kr16',
              'target': '6809 / USIM bare-metal', 'kind': 'runtime',
              'flags': ('optimizer ' + ('off' if args.optimization == '0' else 'on')) if args.compiler == 'c3' else '-O' + args.optimization,
              'revision': env.get('GITHUB_SHA', 'local'), 'rows': [], 'commands': [],
              'emulator': 'USIM bundled with CMOC 0.1.99', 'cycles': None,
              'instruction_scope': 'Four calls including call/return, ABI shims, support functions and runtime helpers; excludes startup and output'}
    (build / 'commands.log').write_text('')

    def run(command, version_probe=False, stderr_file=None):
        report['commands'].append(command)
        result = subprocess.run(command, cwd=build, env=env, capture_output=True,
                                text=True, timeout=60)
        with (build / 'commands.log').open('a') as log:
            log.write(json.dumps(command) + '\n' + result.stdout + result.stderr)
        if stderr_file is not None:
            stderr_file.write_text(result.stderr)
        if not version_probe or result.returncode not in (0, 1):
            result.check_returncode()
        return result.stdout + result.stderr if version_probe else result.stdout

    try:
        if args.compiler == 'c3':
            revision = (ROOT / 'tools/c3-revision.txt').read_text().strip()
            actual = run(['git', '-C', str(c3base), 'rev-parse', 'HEAD']).strip()
            if actual != revision:
                raise ValueError('C3 revision mismatch')
            report['toolchain_revision'] = revision
            report['version'] = 'C3 ' + revision[:12]
            libraries = ['-L' + str(c3base / 'lwbackend'), '-lc3lw']
        elif args.compiler == 'vbcc':
            report['version'] = run(['vbcchc12'], version_probe=True).splitlines()[0]
            report['release'] = '6809 Release 1 Preview (2026-01-25)'
            report['release_url'] = 'http://www.compilers.de/vbcc6809_20260125.zip'
            libraries = ['-L' + str(ROOT / 'build/vbcc/targets/6809-sim/lib'), '-lvc']
        elif args.compiler == 'llvm':
            report['version'] = run(['mc6809-clang', '--version']).splitlines()[0]
            if 'llvm-mc6809 1.0 b9af0417885deb8e878ba50e59f90bb8037577f7' not in report['version']:
                raise ValueError('Unexpected LLVM release version')
            report['release'] = 'RELEASE_1.0'
            report['release_url'] = 'https://github.com/markrvmurray/llvm-mc6809/releases/tag/RELEASE_1.0'
            report['abi_scratch_bytes'] = 24
            libraries = ['-L' + str(ROOT / 'build/llvm/lib/clang/24/lib/mc6809'), '-lclang_rt.builtins', '-L' + str(ROOT / 'build/llvm/lib/clang-runtimes/mc6809/lib'), '-lc']
        else:
            report['version'] = run(['cmoc', '--version']).strip()
            libraries = ['-L' + str(toolchain / 'share/cmoc/lib'), '-lcmoc-std-usim', '-lcmoc-crt-usim']
        if args.compiler == 'vbcc':
            report['assembler_version'] = run(['vasm6809_std'], version_probe=True).splitlines()[0]
            report['linker_version'] = run(['vlink', '-v'], version_probe=True).splitlines()[0]
            # Select ABI branches from the same harness, then translate directives.
            lines, active = [], [True]
            for line in (ROOT / 'adapters/kr16-usim.asm').read_text().splitlines():
                words = line.split()
                if not words or line.lstrip().startswith(';'):
                    continue
                op = words[0]
                if op == 'ifdef':
                    active.append(active[-1] and words[1] == 'VBCC_ABI')
                elif op == 'else':
                    active[-1] = active[-2] and not active[-1]
                elif op == 'endc':
                    active.pop()
                elif active[-1]:
                    if op == 'section':
                        line = '        .section .start,\"ax\"'
                    elif op == 'endsection':
                        continue
                    elif op in ('export', 'import'):
                        line = '        .global ' + words[1]
                    elif not line.startswith(' '):
                        line += ':'
                    lines.append(line.replace('$', '0x'))
            (build / 'harness.s').write_text('\n'.join(lines) + '\n')
            run(['vasm6809_std', '-Fvobj', '-o', 'harness.o', 'harness.s'])
        elif args.compiler == 'llvm':
            report['assembler_version'] = 'LLVM integrated assembler (same release as clang)'
            report['linker_version'] = run(['mc6809-ld', '--version']).strip()
            # Translate only assembler directives/label spelling, preserving the
            # common harness instructions and compiler-specific ABI branches.
            lines = ['.set LLVM_ABI, 1']
            for line in (ROOT / 'adapters/kr16-usim.asm').read_text().splitlines():
                words = line.split()
                if not words or line.lstrip().startswith(';'):
                    lines.append(line)
                    continue
                op = words[0]
                if op == 'section':
                    line = '        .section .start,"ax"'
                elif op == 'endsection':
                    continue
                elif op in ('export', 'import', 'ifdef'):
                    line = '        ' + {'export': '.globl', 'import': '.extern', 'ifdef': '.ifdef'}[op] + ' ' + words[1]
                elif op in ('else', 'endc'):
                    line = '        ' + {'else': '.else', 'endc': '.endif'}[op]
                elif not line.startswith(' '):
                    line += ':'
                lines.append(line.replace('$', '0x'))
            (build / 'harness.s').write_text('\n'.join(lines) + '\n')
            run(['mc6809-clang', '-mcpu=mc6809', '-fno-pie', '-c', 'harness.s', '-o', 'harness.o'])
        else:
            report['assembler_version'] = run(['lwasm', '--version']).strip()
            report['linker_version'] = run(['lwlink', '--version']).strip()
            harness = ['lwasm', '--format=obj', '-o', 'harness.o']
            if args.compiler == 'cmoc':
                harness.append('-DCMOC_ABI')
            run([*harness, str(ROOT / 'adapters/kr16-usim.asm')])
        for reference in REFERENCES:
            name = reference.__name__
            row = {'benchmark': name, 'status': 'FAIL'}
            phase = 'source preparation'
            try:
                objects = []
                row['assembly'] = {}
                hashes = {relative: hashlib.sha256((ROOT / 'benchmarks/kr16' / relative).read_bytes()).hexdigest()
                          for relative in sources(name)}
                row['source_files'] = ['benchmarks/kr16/' + relative for relative in sources(name)]
                row['source_sha256'] = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
                row['source_hashes'] = hashes
                phase = 'compilation'
                for relative in sources(name):
                    source = ROOT / 'benchmarks/kr16' / relative
                    stem = source.stem
                    shutil.copyfile(source, build / source.name)
                    if args.compiler == 'c3':
                        # -a stops BEFORE optimization, and writes beside the source.
                        run(['c3', stem + '.c', '-a'])
                        assembly = stem + '.a'
                        if args.optimization == '2':
                            run(['c3optx', assembly, stem + '.opt.a'])
                            assembly = stem + '.opt.a'
                        run(['c3-as', assembly, '-o=' + stem + '.o'])
                    elif args.compiler == 'vbcc':
                        run(['vbcchc12', '-cpu=6809', '-O=' + ('0' if args.optimization == '0' else '1023'),
                             stem + '.c', '-o=' + stem + '.s'])
                        run(['vasm6809_std', '-nowarn=62', '-opt-branch', '-opt-offset', '-Fvobj',
                             '-o', stem + '.o', stem + '.s'])
                    elif args.compiler == 'llvm':
                        run(['mc6809-clang', '-mcpu=mc6809', '-std=c89', '-fno-pie', '-fno-lto',
                             '-O' + args.optimization, '-save-temps=obj', '-c', '-o', stem + '.o', stem + '.c'])
                    else:
                        run(['cmoc', '--usim', '-O' + args.optimization, '-i', '-c', '-o', stem + '.o', stem + '.c'])
                    assembly_file = (stem + ('.opt.a' if args.optimization == '2' else '.a')) if args.compiler == 'c3' else stem + '.s'
                    row['assembly'][assembly_file] = (build / assembly_file).read_text()
                    objects.append(stem + '.o')
                phase = 'linking'
                if args.compiler == 'vbcc':
                    maptext = run(['vlink', '-b', 'srec19', '-T', str(ROOT / 'adapters/kr16-vbcc.ld'),
                                   '-M', '-o', name + '.srec', 'harness.o', *objects, *libraries])
                    (build / (name + '.map')).write_text(maptext)
                elif args.compiler == 'llvm':
                    run(['mc6809-ld', '-T', str(ROOT / 'adapters/kr16-llvm.ld'),
                         '-Map=' + name + '.map', '-o', name + '.elf', 'harness.o', *objects, *libraries])
                    run(['mc6809-objcopy', '-O', 'srec', name + '.elf', name + '.srec'])
                else:
                    run(['lwlink', '--format=srec', '--script=' + str(ROOT / 'adapters/kr16-usim.link'),
                         '--map=' + name + '.map', '-o', name + '.srec', 'harness.o', *objects, *libraries])
                phase = 'execution'
                maptext = (build / (name + '.map')).read_text()
                row['linker_map'] = maptext
                env['USIM_BENCH_BEGIN'] = format(boundary_address(maptext, 'bench_begin'), 'x')
                env['USIM_BENCH_END'] = format(boundary_address(maptext, 'bench_end'), 'x')
                statistics = build / (name + '.instructions.log')
                output = run(['usim', name + '.srec'], stderr_file=statistics)
                counts = instruction_counts(statistics.read_text(), SEEDS)
                row['instructions_by_seed'] = counts
                row['instructions'] = sum(item['instructions'] for item in counts)
                actual = [tuple(int(word, 16) for word in line.split()) for line in output.splitlines()]
                expected = [(seed, reference(seed)) for seed in SEEDS]
                row.update(status='PASS' if actual == expected else 'FAIL', output=output, expected=expected,
                           loaded_bytes=cmoc_adapter.loaded_bytes(build / (name + '.srec')))
                if actual != expected:
                    row.update(error='Checksum mismatch', failure_stage='verification')
                phase = 'size measurement'
                if args.compiler == 'vbcc':
                    total = 0
                    for obj in objects:
                        sections = re.findall(r'^\s+([0-9a-fA-F]+) - ([0-9a-fA-F]+) ' + re.escape(obj) + r'\(\.text\)', maptext, re.M)
                        if len(sections) != 1:
                            raise ValueError('Expected one vbcc benchmark text section per object')
                        total += int(sections[0][1], 16) - int(sections[0][0], 16)
                    row['kernel_code_bytes'] = total
                elif args.compiler == 'llvm':
                    sizes = run(['mc6809-size', '-A', *objects])
                    sections = re.findall(r'^\.text(?:\.\S+)?\s+(\d+)\s+\d+\s*$', sizes, re.M)
                    if not sections:
                        raise ValueError('No LLVM kernel text section')
                    row['kernel_code_bytes'] = sum(map(int, sections))
                else:
                    maptext = (build / (name + '.map')).read_text()
                    total = 0
                    for obj in objects:
                        sections = re.findall(r'^Section: code \(' + re.escape(obj) + r'\) load at [0-9A-Fa-f]+, length ([0-9A-Fa-f]+)$', maptext, re.M)
                        if len(sections) != 1:
                            raise ValueError('Expected one benchmark code section per object')
                        total += int(sections[0], 16)
                    row['kernel_code_bytes'] = total
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                row.update(status='FAIL', error=str(error), failure_stage=phase)
                if isinstance(error, subprocess.CalledProcessError):
                    row['exit_code'] = error.returncode
                    if phase == 'compilation' and error.returncode in (-11, 139):
                        row['error'] = 'Compiler crashed (segmentation fault, exit ' + str(error.returncode) + ')'
            report['rows'].append(row)
            print(name, row['status'])
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
        print('Infrastructure error:', error)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if len(report['rows']) == len(REFERENCES) and all(r['status'] == 'PASS' for r in report['rows']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
