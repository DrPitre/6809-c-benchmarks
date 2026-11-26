"""Build and execute a separate NitrOS-9 application suite on the real kernel."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
CONFIGURATIONS = [('c300', 'C3 optimizer off', 'c3', '0'),
                  ('c302', 'C3 optimizer on', 'c3', '2'),
                  ('ll00', 'LLVM -O0', 'llvm', '0'), ('ll02', 'LLVM -O2', 'llvm', '2'),
                  ('llos', 'LLVM -Os', 'llvm', 's'), ('lloz', 'LLVM -Oz', 'llvm', 'z'),
                  ('vb00', 'VBCC -O0', 'vbcc', '0'), ('vb02', 'VBCC -O2', 'vbcc', '2')]
APPLICATIONS = {'uniq': ('kreider/uniq/uniq.c', 'uq'), 'dgrep': ('kreider/dgrep/grep.c', 'dg'), 'ed': ('ed/ed.c', 'ed'),
                'cb': ('kreider/cb/cb.c', 'cb'), 'lb': ('kreider/lb/lb.c', 'lb'),
                'ppc': ('kreider/ppc/ppc.c', 'pp')}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module_info(path, expected_name):
    data = Path(path).read_bytes()
    if len(data) < 16 or data[:2] != b'\x87\xcd' or int.from_bytes(data[2:4], 'big') != len(data):
        raise ValueError('invalid OS-9 module header/length')
    parity = 0
    for byte in data[:9]:
        parity ^= byte
    if parity != 255 or data[6] != 0x11:
        raise ValueError('invalid OS-9 header parity/program type')
    crc = 0xffffff
    for byte in data[:-3]:
        crc ^= byte << 16
        for _ in range(8):
            crc = ((crc << 1) ^ (0x800063 if crc & 0x800000 else 0)) & 0xffffff
    if (crc ^ 0xffffff) != int.from_bytes(data[-3:], 'big'):
        raise ValueError('invalid OS-9 module CRC')
    offset = int.from_bytes(data[4:6], 'big')
    name = ''
    for byte in data[offset:-3]:
        name += chr(byte & 127)
        if byte & 128:
            break
    if name.lower() != expected_name.lower():
        raise ValueError('module name must uniquely identify the configuration: ' + name)
    return {'module_bytes': len(data), 'requested_data_bytes': int.from_bytes(data[11:13], 'big'),
            'module_sha256': digest(path), 'module_name': name}


def report_passes(report, expected_rows):
    pointers = report.get('vbcc_pointer_probes', [])
    return (report.get('reached_completion') is True
            and report.get('runtime_probe', {}).get('status') == 'PASS'
            and len(pointers) == 2
            and {p['configuration_id'] for p in pointers} == {'vb00', 'vb02'}
            and all(p['status'] == 'PASS' for p in pointers)
            and len(report['rows']) == expected_rows
            and all(r['status'] == 'PASS' for r in report['rows']))


def fixture_bytes(value):
    """Decode fixture bytes without applying text conversion to binary data."""
    if isinstance(value, dict):
        if 'hex' in value:
            return bytes.fromhex(value['hex'])
        value = value['text']
    return value.replace('\n', '\r').encode('ascii')


def normalize(data):
    return data.replace(b'\r\n', b'\n').replace(b'\r', b'\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', type=Path, required=True)
    parser.add_argument('--configuration', action='append', help='Limit to named config IDs for local checks')
    parser.add_argument('--runtime-probe', type=Path, default=ROOT / 'build/sources/picolibc/test/test-stdio/test-os9-text.c')
    parser.add_argument('--wall-seconds', type=int, default=180)
    args = parser.parse_args()
    work = ROOT / 'build/os9-apps'
    work.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    c3 = ROOT / 'build/sources/nitros9-languages/c3'
    vbcc = ROOT / 'build/vbcc'
    llvm = ROOT / 'build/llvm/bin/mc6809-os9-clang'
    toolbin = ROOT / 'build/toolchain/bin'
    env.update(C3BASE=str(c3), C3LW_HOME=str(c3 / 'lwbackend'))
    env['PATH'] = os.pathsep.join(str(c3 / 'build/unix' / stage) for stage in ('exec', 'prep', 'comp', 'optx')) + os.pathsep + str(c3 / 'lwbackend') + os.pathsep + str(toolbin) + os.pathsep + env['PATH']
    os9 = str(toolbin / 'os9')
    machine = ROOT / 'build/sources/markrvmurray-usim/usim09pt'
    recipe = ROOT / 'build/sources/nitros9/recipes/picothing/l2'
    sources = json.loads((ROOT / 'tools/os9-app-sources.json').read_text())
    report = {'suite': 'os9-apps', 'kind': 'application-runtime', 'compiler': 'NitrOS-9 applications',
              'target': 'NitrOS-9 Level 2 / Pico-Thing / 6809', 'flags': 'per configuration',
              'revision': env.get('GITHUB_SHA', 'local'), 'sources': sources,
              'patch_sha256': digest(ROOT / 'benchmarks/os9-apps/portable.patch'),
              'fixture_sha256': digest(ROOT / 'benchmarks/os9-apps/cases.json'),
              'kernel_disk_sha256': digest(recipe / 'bench.dsk'),
              'firmware_sha256': digest(recipe / 'rel_picothing.srec'),
              'emulator_revision': (ROOT / 'tools/usim-revision.txt').read_text().strip(),
              'compiler_versions': {'C3': (ROOT / 'tools/c3-revision.txt').read_text().strip(),
                                    'LLVM': (ROOT / 'build/llvm/VERSION').read_text().strip(),
                                    'VBCC': '6809 Release 1 Preview 2026-01-25; archive SHA-256 18db043d4d4c8b0a16d4fa4b813616f277fcfb3667be0eda2334a8b8b024917e'},
              'vbcc_compiler_patch': json.loads((vbcc / 'COMPILER-PATCH.json').read_text()),
              'vbcc_os9_runtime': json.loads((vbcc / 'OS9-RUNTIME.json').read_text()),
              'llvm_runtime': json.loads((ROOT / 'build/llvm/OS9-RUNTIME.json').read_text()),
              'rows': [], 'commands': []}

    if digest(vbcc / 'bin/vbcchc12') != report['vbcc_compiler_patch']['compiler_sha256']:
        raise ValueError('VBCC compiler does not match the source-build manifest')

    def run(command, cwd=work, check=True):
        report['commands'].append(command)
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=60)
        with (work / 'commands.log').open('ab') as log:
            log.write((json.dumps(command) + '\n').encode() + result.stdout + result.stderr)
        if check:
            result.check_returncode()
        return result

    def build_vbcc(folder, source_names, name, optimization):
        objects = []
        for source_name in source_names:
            stem = Path(source_name).stem
            run([str(vbcc / 'bin/vbcchc12'), '-cpu=6809', '-pcrel', '-drel',
                 '-I' + str(vbcc / 'targets/6809-os9/include'), '-O=' + ('0' if optimization == '0' else '1023'),
                 source_name, '-o=' + stem + '.s'], folder)
            run([str(vbcc / 'bin/vasm6809_std'), '-quiet', '-Fvobj', '-nowarn=62', '-opt-branch', '-opt-offset',
                 stem + '.s', '-o', stem + '.o'], folder)
            objects.append(stem + '.o')
        run([str(vbcc / 'bin/vlink'), '-bos9-6809', '-L' + str(vbcc / 'targets/6809-os9/lib'),
             str(vbcc / 'targets/6809-os9/lib/startup.o'),
             str(vbcc / 'targets/6809-os9/lib/bench-rw.o'), *objects, '-o', name, '-lvc', '-los9'], folder)

    (work / 'commands.log').write_text('')
    cases = json.loads((ROOT / 'benchmarks/os9-apps/cases.json').read_text())
    selected = [c for c in CONFIGURATIONS if not args.configuration or c[0] in args.configuration]
    if not selected:
        parser.error('no valid configurations selected')
    source_copy = work / 'source'
    source_copy.mkdir(exist_ok=True)
    for app, (relative, _) in APPLICATIONS.items():
        destination = source_copy / Path(relative).parent
        destination.mkdir(parents=True, exist_ok=True)
        for source in (ROOT / 'build/sources/nitros9-apps' / Path(relative).parent).glob('*'):
            if source.suffix in ('.c', '.h'):
                shutil.copyfile(source, destination / source.name)
    run(['patch', '--batch', '-p1', '-i', str(ROOT / 'benchmarks/os9-apps/portable.patch')], source_copy)
    shutil.copyfile(ROOT / 'benchmarks/os9-apps/ppc-clock.c', source_copy / 'kreider/ppc/ppc-clock.c')
    report['ppc_clock'] = {'timestamp': '2026-11-26 13:45:06',
                           'source_sha256': digest(ROOT / 'benchmarks/os9-apps/ppc-clock.c')}
    pending = []
    for config, label, compiler, optimization in selected:
        for app, (relative, prefix) in APPLICATIONS.items():
            folder = work / config / app
            folder.mkdir(parents=True, exist_ok=True)
            for source in (source_copy / Path(relative).parent).iterdir():
                shutil.copyfile(source, folder / source.name)
            source_names = sorted(p.name for p in folder.glob('*.c'))
            prepared = {p.name: digest(p) for p in sorted(folder.iterdir()) if p.suffix in ('.c', '.h')}
            name = prefix + config  # Six characters for every configuration: equal name overhead.
            row = {'application': app, 'configuration': label, 'configuration_id': config,
                   'benchmark': app, 'status': 'FAIL', 'stage': 'build', 'cases': [],
                   'prepared_sources_sha256': prepared,
                   'source_file': relative, 'prepared_source_sha256': digest(folder / Path(relative).name)}
            report['rows'].append(row)
            (folder / name).unlink(missing_ok=True)
            try:
                if compiler == 'c3':
                    run(['c3', '-y', '-q', *(['-dBENCH_C3'] if app in ('ed', 'lb', 'ppc') else []), *source_names, *(['-o'] if optimization == '0' else []), '-f=' + name], folder)
                elif compiler == 'llvm':
                    run([str(llvm), '-mcpu=mc6809', '-std=gnu89', '-Wno-implicit-int',
                         '-Wno-implicit-function-declaration', '-Wno-deprecated-non-prototype',
                         '-O' + optimization, '-Wl,-Map=' + name + '.map', *source_names, '-o', name], folder)
                else:
                    build_vbcc(folder, source_names, name, optimization)
                row.update(module_info(folder / name, name))
                row['stage'] = 'execution'
                pending.append((row, folder / name))
                print(label, app, 'LINKED', row['module_bytes'], flush=True)
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                row['error'] = str(error)
                print(label, app, 'BUILD FAIL', flush=True)
    disk = work / 'test.dsk'
    shutil.copyfile(recipe / 'bench.dsk', disk)
    for directory in ('BENCH', 'BENCH/CMDS'):
        run([os9, 'makdir', str(disk) + ',' + directory])
    startup = ['chx /dd/bench/cmds', 'chd /dd/bench', 'echo APPBEGIN']
    for i, case in enumerate(cases):
        path = work / ('in' + str(i))
        path.write_bytes(bytes.fromhex(case['input_hex']) if 'input_hex' in case else fixture_bytes(case['input']))
        run([os9, 'copy', '-r', str(path), str(disk) + ',BENCH/in' + str(i)])
    for row, module in pending:
        run([os9, 'copy', '-r', str(module), str(disk) + ',BENCH/CMDS/' + module.name])
        run([os9, 'attr', '-q', '-e', '-pe', '-pr', str(disk) + ',BENCH/CMDS/' + module.name])
        for i, case in enumerate(cases):
            if case['app'] != row['application']:
                continue
            directory = ('d' + row['configuration_id'] + str(i) + '/') if case.get('isolated') else ''
            if directory:
                run([os9, 'makdir', str(disk) + ',BENCH/' + directory.rstrip('/')])
                run([os9, 'copy', '-r', str(work / ('in' + str(i))), str(disk) + ',BENCH/' + directory + 'in' + str(i)])
                startup.append('chd /dd/bench/' + directory.rstrip('/'))
            output_name = 'o' + row['configuration_id'] + str(i)
            input_name = 'in' + str(i)
            replacements = {}
            file_checks = []
            for kind in ('files', 'output_files'):
                for j, (token, contents) in enumerate(case.get(kind, {}).items()):
                    disk_name = (contents.get('path') if isinstance(contents, dict) else None)
                    disk_name = disk_name or (('f' if kind == 'files' else 's') + row['configuration_id'] + str(i) + str(j))
                    replacements['@' + token + '@'] = disk_name
                    if kind == 'files':
                        resource = work / ('resource-' + row['configuration_id'] + str(i) + str(j))
                        resource.write_bytes(fixture_bytes(contents))
                        run([os9, 'copy', '-r', str(resource), str(disk) + ',BENCH/' + directory + disk_name])
                    else:
                        check = {'id': token, 'output_file': directory + disk_name, 'status': 'NOT RUN'}
                        if isinstance(contents, dict) and 'hex' in contents:
                            check['expected_hex'] = contents['hex']
                        else:
                            check['expected'] = contents['text'] if isinstance(contents, dict) else contents
                        file_checks.append(check)
            if replacements and 'input' in case:
                input_name = 'c' + row['configuration_id'] + str(i)
                commands = case['input']
                for token, replacement in replacements.items():
                    commands = commands.replace(token, replacement)
                resource = work / input_name
                resource.write_bytes(fixture_bytes(commands))
                run([os9, 'copy', '-r', str(resource), str(disk) + ',BENCH/' + directory + input_name])
            arguments = [('in' + str(i)) if arg == 'INPUT' else arg for arg in case['args']]
            for token, replacement in replacements.items():
                arguments = [arg.replace(token, replacement) for arg in arguments]
            words = [module.name] + arguments
            command = ' '.join(words)
            if 'INPUT' not in case['args']:
                command += ' <' + input_name
            startup.append('echo CASE' + row['configuration_id'] + str(i))
            startup.append(command + ' >' + output_name)
            if directory:
                startup.append('chd /dd/bench')
            row['cases'].append({'id': case['id'], 'output_file': directory + output_name,
                                 'expected': case['output'], 'files': file_checks, 'status': 'NOT RUN'})
    report['vbcc_pointer_probes'] = []
    for config, optimization in (('vb00', '0'), ('vb02', '2')):
        folder = work / ('pointer-' + config)
        folder.mkdir(exist_ok=True)
        names = ['array-offset.c', 'offset-check.c']
        for source in names:
            shutil.copyfile(ROOT / 'patches/vbcc-array-offset' / source, folder / source)
        name = 'ar' + config
        build_vbcc(folder, names, name, optimization)
        item = {'configuration_id': config, 'status': 'FAIL', 'output_file': name + '.out',
                'sources_sha256': {n: digest(folder / n) for n in names},
                **module_info(folder / name, name)}
        report['vbcc_pointer_probes'].append(item)
        run([os9, 'copy', '-r', str(folder / name), str(disk) + ',BENCH/CMDS/' + name])
        run([os9, 'attr', '-q', '-e', '-pe', '-pr', str(disk) + ',BENCH/CMDS/' + name])
        startup.extend(['echo POINTER' + config, name + ' >' + item['output_file'], 'echo POINTEREND'])
    probe = work / 'iotest'
    run([str(llvm), '-mcpu=mc6809', '-O2', str(args.runtime_probe), '-o', str(probe)])
    report['runtime_probe'] = {'status': 'FAIL', 'source_sha256': digest(args.runtime_probe),
                               **module_info(probe, 'iotest')}
    run([os9, 'copy', '-r', str(probe), str(disk) + ',BENCH/CMDS/iotest'])
    run([os9, 'attr', '-q', '-e', '-pe', '-pr', str(disk) + ',BENCH/CMDS/iotest'])
    (work / 'rtin').write_bytes(b'one\rtwo\r')
    run([os9, 'copy', '-r', str(work / 'rtin'), str(disk) + ',BENCH/rtin'])
    startup.extend(['echo RUNTIMEBEGIN', 'iotest stdin <rtin >rtout >>rterr', 'echo RUNTIMEEND'])
    startup.append('echo APPDONE')
    (work / 'startup').write_bytes(('\r'.join(startup) + '\r').encode('ascii'))
    run([os9, 'copy', '-r', str(work / 'startup'), str(disk) + ',startup'])
    run([os9, 'attr', '-q', '-npe', '-npw', '-pr', '-ne', '-w', '-r', str(disk) + ',startup'])
    (work / 'state.fram').unlink(missing_ok=True)
    log = work / 'console.log'
    ready = False
    command = [str(machine), '--timeout=3000000000', '-f', str(work / 'state.fram'),
               '-d', str(disk), str(recipe / 'rel_picothing.srec')]
    report['commands'].append(command)
    with log.open('wb') as output:
        process = subprocess.Popen(command, cwd=work, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
        start = time.monotonic()
        while process.poll() is None and time.monotonic() - start < args.wall_seconds:
            if re.search(rb'(^|\n)APPDONE\n', normalize(log.read_bytes().replace(b'\0', b''))):
                ready = True
                break
            time.sleep(1)
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=10)
    report['reached_completion'] = ready
    report['console_log'] = log.read_bytes().replace(b'\0', b'').decode('ascii', errors='replace')
    for item in report['vbcc_pointer_probes']:
        destination = work / item['output_file']
        destination.unlink(missing_ok=True)
        result = run([os9, 'copy', '-r', str(disk) + ',BENCH/' + item['output_file'], str(destination)], check=False)
        raw = destination.read_bytes() if destination.exists() else b''
        item['actual'] = raw.decode('ascii', errors='replace')
        marker = ('POINTER' + item['configuration_id'] + '\n').encode()
        console = normalize(log.read_bytes().replace(b'\0', b''))
        segment = console.split(marker, 1)[-1].split(b'POINTEREND', 1)[0]
        if (ready and marker in console and result.returncode == 0 and raw == b'ARRAY-OFFSET PASS\r'
                and not re.search(rb'(?i)(error\s*#|WHAT\?)', segment)):
            item['status'] = 'PASS'
        print('VBCC array-offset regression', item['configuration_id'], item['status'], flush=True)
    for name in ('rtout', 'rterr'):
        destination = work / (name + '.txt')
        destination.unlink(missing_ok=True)
        result = run([os9, 'copy', '-r', str(disk) + ',BENCH/' + name, str(destination)], check=False)
        raw = destination.read_bytes() if destination.exists() else b''
        report['runtime_probe'][name] = raw.decode('ascii', errors='replace')
    runtime_console = normalize(log.read_bytes().replace(b'\0', b'')).split(b'RUNTIMEBEGIN\n', 1)[-1].split(b'RUNTIMEEND\n', 1)[0]
    if ready and not re.search(rb'(?i)(error\s*#|WHAT\?)', runtime_console) and report['runtime_probe']['rtout'] == 'OS9TEXT PASS\r' and report['runtime_probe']['rterr'] == 'OS9TEXT STDERR\r':
        report['runtime_probe']['status'] = 'PASS'
    print('OS-9 text/binary runtime regression', report['runtime_probe']['status'], flush=True)
    console = normalize(log.read_bytes().replace(b'\0', b''))
    for row, module in pending:
        for case in row['cases']:
            host = work / (case['output_file'] + '.txt')
            host.parent.mkdir(parents=True, exist_ok=True)
            host.unlink(missing_ok=True)
            result = run([os9, 'copy', '-r', str(disk) + ',BENCH/' + case['output_file'], str(host)], check=False)
            actual = normalize(host.read_bytes()).decode('ascii', errors='replace') if host.exists() else None
            case['actual'] = actual
            case['copied'] = result.returncode == 0
            for saved in case.get('files', []):
                destination = work / (saved['output_file'] + '.txt')
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.unlink(missing_ok=True)
                copied = run([os9, 'copy', '-r', str(disk) + ',BENCH/' + saved['output_file'], str(destination)], check=False)
                raw = destination.read_bytes() if destination.exists() else None
                saved['copied'] = copied.returncode == 0
                saved['actual'] = raw.decode('ascii', errors='replace') if raw is not None else None
                if 'expected_hex' in saved:
                    saved['actual_hex'] = raw.hex() if raw is not None else None
                    expected = bytes.fromhex(saved['expected_hex'])
                else:
                    expected = fixture_bytes(saved['expected'])
                saved['status'] = 'PASS' if copied.returncode == 0 and raw == expected else 'FAIL'
            fixture_index = next(i for i, fixture in enumerate(cases)
                                 if fixture['app'] == row['application'] and fixture['id'] == case['id'])
            marker = ('CASE' + row['configuration_id'] + str(fixture_index) + '\n').encode()
            segment = console.split(marker, 1)[-1].split(b'CASE', 1)[0].split(b'APPDONE', 1)[0]
            executed = marker in console and not re.search(rb'(?i)(error\s*#|WHAT\?)', segment)
            case['execution_completed'] = ready and executed
            case['status'] = 'PASS' if ready and executed and result.returncode == 0 and actual == case['expected'] and all(f['status'] == 'PASS' for f in case.get('files', [])) else 'FAIL'
        row['status'] = 'PASS' if row['cases'] and all(c['status'] == 'PASS' for c in row['cases']) else 'FAIL'
        if row['status'] != 'PASS':
            row['error'] = 'OS-9 execution did not complete or fixture output mismatch'
        print(row['configuration'], row['application'], row['status'], flush=True)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report_passes(report, len(selected) * len(APPLICATIONS)) else 1


if __name__ == '__main__':
    raise SystemExit(main())
