"""Check shared kr16 kernels on a host with independent Python references."""
import os
from pathlib import Path
import shlex
import subprocess
from check import SEEDS, crc16, insertion_sort, mix16

ROOT = Path(__file__).resolve().parents[1]
build = ROOT / 'build/kr16-host'
build.mkdir(parents=True, exist_ok=True)
cc = shlex.split(os.environ.get('CC', 'cc'))
flags = shlex.split(os.environ.get('CFLAGS', '-O2 -std=c89 -pedantic -Wall -Wextra'))
subprocess.run([*cc, *flags, '-c', str(ROOT / 'adapters/kr16-host.c'), '-o', str(build / 'runner.o')], check=True)
for reference in (crc16, insertion_sort, mix16):
    name = reference.__name__
    obj = build / (name + '.o')
    binary = build / name
    subprocess.run([*cc, *flags, '-c', str(ROOT / 'benchmarks/kr16' / (name + '.c')), '-o', str(obj)], check=True)
    subprocess.run([*cc, str(obj), str(build / 'runner.o'), '-o', str(binary)], check=True)
    actual = [tuple(map(int, line.split())) for line in subprocess.check_output([str(binary)], text=True, timeout=10).splitlines()]
    if actual != [(seed, reference(seed)) for seed in SEEDS]:
        raise SystemExit('FAIL kr16 ' + name)
    print('PASS kr16 ' + name)
