"""Exhaustively check NEG results and NZVC in USIM; requires LWASM."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--lwasm', default='lwasm')
parser.add_argument('--usim', default='usim')
args = parser.parse_args()
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    for mode in ('a', 'b', 'direct', 'indexed', 'extended'):
        lines = [' org $2800', ' lds #$fe00', ' clra', ' tfr a,dp', ' ldx #$1000']
        for value in range(256):
            result = (-value) & 255
            flags = (8 if result & 128 else 0) | (4 if result == 0 else 0) | (2 if value == 128 else 0) | (1 if value else 0)
            lines += [f' lda #{value}']
            if mode == 'a':
                lines += [' nega']
            elif mode == 'b':
                lines += [' tfr a,b', ' negb', ' tfr b,a']
            else:
                operand = {'direct': '<$40', 'indexed': ',x', 'extended': '>$1000'}[mode]
                lines += [f' sta {operand}', f' neg {operand}', ' tfr cc,b', f' lda {operand}']
                # LDA changes NZV; CC was already captured in B.
            if mode in ('a', 'b'):
                lines += [' tfr cc,b']
            lines += [f' cmpa #{result}', ' lbne fail', ' andb #15', f' cmpb #{flags}', ' lbne fail']
        lines += [' ldd #0', ' sync', 'fail ldd #1', ' sync', ' end $2800']
        source = path / (mode + '.asm')
        output = path / (mode + '.srec')
        source.write_text('\n'.join(lines) + '\n')
        subprocess.run([args.lwasm, '--format=srec', '-o', str(output), str(source)], check=True)
        subprocess.run([args.usim, str(output)], check=True, timeout=10)
        print(f'{mode}: all 256 inputs passed (result and NZVC)')
    source = Path(__file__).resolve().with_name('neg16.asm')
    output = path / 'neg16.srec'
    subprocess.run([args.lwasm, '--format=srec', '-o', str(output), str(source)], check=True)
    subprocess.run([args.usim, str(output)], check=True, timeout=10)
    print('16-bit negation: all 65,536 inputs passed')
