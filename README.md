# 6809 C compiler benchmarks

A starter suite for comparing C compilers targeting the Motorola 6809.
The CoCo is one possible execution platform, alongside OS-9 and other
6809 systems. Baseline results must use the 6809 instruction set; 6309
extensions belong in separately labeled comparisons.

## Current status

The shared **kr16** suite runs identical K&R-compatible sources under both
C3 (C-Cubed) and CMOC on a bare-metal 6809 simulator. Both compilers are checked
with optimization disabled and enabled. All three kernels must match independent
reference results for four seeds before their sizes enter the comparison.

The original C89 suite remains available. CMOC runs it; C3's source-compatibility
limitations appear separately in collapsed diagnostics on the published page.
Cycle timing is not implemented yet.

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
built from the CMOC release. The two CMOC and two C3 jobs each record shared kr16 results as well as
the original-suite results. Together with four host reports, this produces
twelve reports. Host jobs also verify the kr16 algorithms.

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

## C3 (C-Cubed) and the shared kr16 suite

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

The original C89 diagnostic section labels these as **COMPILE FAIL**.
The primary kr16 comparison compiles and executes C3 code successfully.
Compatibility jobs succeed when all attempts are recorded after the smoke
link succeeds; broken toolchain setup still fails CI. Neither the OS-9 smoke module nor compatibility probes are executed.
C3 runtime results come from the shared bare-metal kr16 adapter below.
OS-9 application execution and cycle timing remain future work.

### Run shared runtime comparisons

After building the pinned tools above:

```sh
python3 tools/check-kr16.py
python3 tools/run-kr16.py --compiler c3 --optimization 0 --json build/reports/kr16-c3-O0.json
python3 tools/run-kr16.py --compiler c3 --optimization 2 --json build/reports/kr16-c3-O2.json
python3 tools/run-kr16.py --compiler cmoc --optimization 0 --json build/reports/kr16-cmoc-O0.json
python3 tools/run-kr16.py --compiler cmoc --optimization 2 --json build/reports/kr16-cmoc-O2.json
python3 tools/matrix.py build/reports build/site
```

For C3, `--optimization 2` selects its default `c3optx` optimizer, not a C3
`-O2` option; `0` skips it. C3's `-a` stops before optimization, so the adapter
explicitly runs `c3optx` before assembling. Each compiler receives exactly the
same kernel source; reports record SHA-256 hashes and the matrix rejects
mismatches. Assembly, objects, executables, maps, and command logs are retained.

`kr16` is a distinct workload variant, not a silent rewrite of the original
suite. It uses K&R definitions, `unsigned` arithmetic explicitly masked to
16 bits, and no standard headers. The sort stores values 0..255 in unsigned
words and uses 16-bit multiplication, whereas the original sorts bytes and
uses 32-bit arithmetic. Checksum expectations are the same, but size results
must only be compared within the same suite.

The shared assembly harness supplies each seed in D and on the stack to cover
C3 and CMOC calling conventions, then prints the returned 16-bit checksum.
It loads at $2800 with stack top $FE00 and a reserved 4 KiB stack region; these
bounded kernels use no static storage. C3's `_stkcheck` calls use a no-op stub,
so this is a bare-metal kernel comparison, not an OS-9 runtime comparison.
Only referenced compiler helper routines are linked. Kernel size excludes
those helpers; loaded-program size includes them and the common harness.
