# 6809 C compiler benchmarks

A starter suite for comparing C compilers targeting the Motorola 6809.
The CoCo is one possible execution platform, alongside OS-9 and other
6809 systems. Baseline results must use the 6809 instruction set; 6309
extensions belong in separately labeled comparisons.

## Current status

Three C89 kernels run on the host and on an emulated Motorola 6809 using
CMOC 0.1.99 and its bundled USIM simulator. CI publishes correctness and
6809 code/program sizes at `-O0` and `-O2`. C3 (C-Cubed) is also tested for compile compatibility; the current C89
kernels are rejected, so C3 execution and performance remain unmeasured.
Cycle timing is not implemented yet. Host results remain a separate sanity check.

## Run the checks

Requires a host C compiler, Make, and Python 3:

```sh
make check
```

Override `CC` and `CFLAGS` to check another host compiler or optimization level.
Run `make clean` when changing flags, since Make does not track flag changes.

| Kernel | Work performed |
| --- | --- |
| crc16 | CRC-16/CCITT over bytes 0 through 255 |
| insertion_sort | Generate and sort 64 bytes; compute an ordered checksum |
| mix16 | 1,024 rounds of 16-bit shifts, XOR, and addition |

Kernels use no I/O or allocation. The sort workload includes data generation
and checksum costs, including 32-bit arithmetic. Each kernel returns a checksum
for a supplied seed. Four seeds are checked against independent Python models.
The data model requires 8-bit bytes and 16-bit unsigned short; unsigned int
may be 16 or 32 bits. Historical dialect limitations should be recorded explicitly.

## GitHub Actions

The workflow builds and checks kernels on pushes, pull requests, and manual
runs using host GCC/Clang and 6809 CMOC, each at `-O0` and `-O2`. CMOC 0.1.99
and LWTOOLS 4.24 are built from SHA-256-verified release archives. USIM is
built from the CMOC release. Two additional C3 compatibility jobs complete the eight-report matrix.

## Comparison rules

- Compile the runner and kernel separately; disable link-time optimization.
- Verify output on the execution target before accepting measurements.
- Record the compiler version, exact commands, flags, source revision, ABI,
  platform, CPU, and emulator or hardware configuration.
- Measure cycles around `bench_run`, excluding runner I/O. Document call and
  timer overhead, interrupt handling, repetitions, and subtraction methods.
- Distinguish kernel code/data size, linked runtime size, and complete executable
  size. Include compiler helper routines in a documented size accounting method.
- Keep bare-metal and OS-9 comparisons separate. Compare matching optimization
  goals and publish all flags. Do not infer cycle counts from host elapsed time.

## Adding a 6809 toolchain

See [adapters/README.md](adapters/README.md) for the adapter contract and
[results/README.md](results/README.md) for required measurement metadata.
Start with one verified compiler/target combination, then add a second using
the same kernels and measurement boundaries. Compiler binaries and ROM images
are not bundled.

## Published matrix

CI collects JSON results from every compiler/optimization job and generates a
benchmark-by-compiler matrix. Failed checks remain visible as FAIL; missing
report artifacts block publication. Every run includes a job summary and a
downloadable `benchmark-matrix` artifact. Main-branch runs deploy the HTML, Markdown, and JSON report to the
[live matrix](https://drpitre.github.io/6809-c-benchmarks/). Pages is enabled
for this repository; forks should select GitHub Actions as their Pages source.

The deployment follows the [GitHub Pages custom workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

To preview a local report:

```sh
make check
BENCH_CC=cc BENCH_FLAGS=-O2 python3 tools/check.py --json build/reports/local.json
python3 tools/matrix.py build/reports build/site
```

Open `build/site/index.html`. Local results describe only the compiler and flags
you actually used; set the metadata variables accordingly.

## Run the 6809 adapter

On Ubuntu, install `build-essential bison flex curl python3`, then:

```sh
sh tools/build-cmoc.sh
export PATH="$PWD/build/toolchain/bin:$PATH"
python3 tools/run-cmoc.py --optimization 0 --json build/reports/cmoc-O0.json
python3 tools/run-cmoc.py --optimization 2 --json build/reports/cmoc-O2.json
python3 tools/matrix.py build/reports build/site
```

The build stays under `build/`. `CMOC` and `USIM` may override executable paths
for an existing installation; LWTOOLS must also be on PATH. Each kernel and
runner are compiled separately. Each run has a 60-second timeout. Reports
include compiler/assembler/linker versions, exact command arguments, checksums,
and sizes. CI retains assembly, S-record executables, maps, and command logs.

CMOC has no `limits.h`; `bench.h` uses its documented 8-bit-byte data model
and a compile-time short-size check. The benchmark algorithms are unchanged.
The USIM adapter uses CMOC's `cmoc.h` for output.

Kernel code size is the kernel object's `code` section, excluding linked
helpers. Loaded program size counts unique S-record data bytes, including
startup, runner, initialized data, and linked runtime, but excluding BSS and
S-record text overhead. These metrics are distinct and are not standalone
kernel footprint measurements. Timing is not measured by this adapter.

The CMOC archive uses the author's HTTP hosting address; its pinned SHA-256
must match before extraction. The digest was also checked against a preexisting
local release archive. LWTOOLS is downloaded over HTTPS.

## C3 (C-Cubed) compatibility

C3 comes from [nitros9-languages](https://github.com/nitros9project/nitros9-languages/tree/e6e1a014c092fafc5e1378195ad33659b4e54676/c3),
pinned by `tools/c3-revision.txt`. Host builds enable glibc default API
declarations with `CPPFLAGS=-D_DEFAULT_SOURCE` while preserving upstream
C89 compiler flags. Both its default optimizer and `-o`
(optimizer disabled) are tested. This is the Microware-derived 6809 compiler,
not the unrelated C3 programming language.

```sh
sh tools/build-cmoc.sh  # supplies pinned LWTOOLS; existing builds may be reused
sh tools/build-c3.sh
python3 tools/run-c3.py --optimizer on --json build/reports/c3-on.json
python3 tools/run-c3.py --optimizer off --json build/reports/c3-off.json
python3 tools/matrix.py build/reports build/site
```

C3 first links a known-supported K&R smoke program to an OS-9 module. It then
compiles small language probes and attempts each unchanged benchmark, retaining
compiler diagnostics and exit codes. The source does not supply `limits.h`;
independent probes also reject `unsigned short`, `unsigned long`, and
`U`-suffixed literals. A typed unsigned parameter probe is accepted.

The matrix labels these as **COMPILE FAIL**, not runtime correctness failures.
Compatibility jobs succeed when all attempts are recorded after the smoke
link succeeds; broken toolchain setup still fails CI. Neither the smoke module
nor accepted probes are executed. No C3 benchmark sizes or cycles are claimed.
OS-9 execution and explicitly named K&R benchmark variants are future work;
variants must be compared using the same source on every compiler.
