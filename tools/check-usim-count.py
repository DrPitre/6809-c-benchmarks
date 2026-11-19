"""Check the patched USIM counter against a hand-counted 6809 program."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
binpath = root / 'build/toolchain/bin'
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    (path / 'count.asm').write_text('''        org $2800
        lds #$fe00
        lbsr sample
        lbsr sample
        ldd #0
        sync
        org $2900
sample  ldy #3
loop    leay -1,y
        bne loop
        lbsr sub
        jmp finish
        org $2920
finish  rts
sub     nop
        rts
        end $2800
''')
    # LDY=1, LEAY/BNE=6, LBSR/NOP/RTS=3, JMP=1 => 11 each call.
    subprocess.run([str(binpath / 'lwasm'), '--format=srec', '-o', str(path / 'count.srec'),
                    str(path / 'count.asm')], check=True)
    env = dict(os.environ, USIM_BENCH_BEGIN='2900', USIM_BENCH_END='2920')
    result = subprocess.run([str(binpath / 'usim'), str(path / 'count.srec')],
                            env=env, capture_output=True, text=True, check=True, timeout=5)
    assert result.stderr.splitlines() == ['BENCH_INSTRUCTIONS 11'] * 2, result.stderr
    assert result.stdout == '', result.stdout
print('USIM instruction counter: two calls of 11 instructions verified')
