"""Check the benchmark machine's I/O, loading, failure, and limit contracts."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
binpath = root / 'build/toolchain/bin'
env = {key: value for key, value in os.environ.items()
       if key not in ('USIM_BENCH_BEGIN', 'USIM_BENCH_END', 'USIM_MAX_INSTRUCTIONS')}
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)

    def assemble(body):
        source = path / 'machine.asm'
        source.write_text(' org $3500\nentry lds #$fe00\n' + body + '\n end entry\n')
        output = path / 'machine.srec'
        subprocess.run([str(binpath / 'lwasm'), '--format=srec', '-o', str(output),
                        str(source)], check=True)
        return output

    def run(output, extra=None):
        return subprocess.run([str(binpath / 'usim'), str(output)], env=dict(env, **(extra or {})),
                              capture_output=True, text=True, timeout=5)

    output = assemble(' lda #65\n sta $ff00\n lda #13\n sta $ff00\n ldd #0\n sync')
    result = run(output)
    assert result.returncode == 0 and result.stdout == 'A\n', result
    # Entry is intentionally not $2800; execution must follow the S9 record.
    for status in (1, 256, 65535):
        assert run(assemble(f' ldd #{status}\n sync')).returncode != 0
    assert run(assemble(' fcb $15')).returncode != 0
    result = run(assemble('loop bra loop'), {'USIM_MAX_INSTRUCTIONS': '10'})
    assert result.returncode != 0 and 'instruction limit' in result.stderr, result
    output = assemble(' ldd #0\n sync')
    for extra in ({'USIM_BENCH_BEGIN': '3500'},
                  {'USIM_BENCH_BEGIN': '3500', 'USIM_BENCH_END': '3500'},
                  {'USIM_BENCH_BEGIN': '3500', 'USIM_BENCH_END': '3600'},
                  {'USIM_BENCH_BEGIN': 'zzzz', 'USIM_BENCH_END': '3600'}):
        assert run(output, extra).returncode != 0, extra
    original = output.read_text()
    lines = original.splitlines()
    lines[0] = lines[0][:-1] + ('0' if lines[0][-1] != '0' else '1')
    output.write_text('\n'.join(lines) + '\n')
    assert run(output).returncode != 0
    output.write_text('\n'.join(line for line in original.splitlines() if not line.startswith('S9')) + '\n')
    assert run(output).returncode != 0
    output.write_text('S1broken\n')
    assert run(output).returncode != 0
print('USIM machine: entry point, console, exit, invalid input, boundaries and limit verified')
