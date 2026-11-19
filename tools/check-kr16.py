"""Check shared kr16 kernels on a host with independent Python references."""
import os
from pathlib import Path
import shlex
import subprocess
from check import SEEDS
from shared_suite import REFERENCES, sources

ROOT = Path(__file__).resolve().parents[1]
build = ROOT / 'build/kr16-host'
build.mkdir(parents=True, exist_ok=True)
cc = shlex.split(os.environ.get('CC', 'cc'))
flags = shlex.split(os.environ.get('CFLAGS', '-O2 -std=c89 -pedantic -Wall -Wextra'))
subprocess.run([*cc, *flags, '-c', str(ROOT / 'adapters/kr16-host.c'), '-o', str(build / 'runner.o')], check=True)
for reference in REFERENCES:
    name = reference.__name__
    objects = []
    for source in sources(name):
        obj = build / (Path(source).stem + '.o')
        subprocess.run([*cc, *flags, '-c', str(ROOT / 'benchmarks/kr16' / source), '-o', str(obj)], check=True)
        objects.append(str(obj))
    binary = build / name
    subprocess.run([*cc, *objects, str(build / 'runner.o'), '-o', str(binary)], check=True)
    actual = [tuple(map(int, line.split())) for line in subprocess.check_output([str(binary)], text=True, timeout=10).splitlines()]
    if actual != [(seed, reference(seed)) for seed in SEEDS]:
        raise SystemExit('FAIL kr16 ' + name)
    print('PASS kr16 ' + name)
