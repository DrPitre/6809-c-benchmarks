# 6809 C compiler benchmarks

A starter suite for comparing C compilers targeting the Motorola 6809.
The CoCo is one possible execution platform, alongside OS-9 and other
6809 systems. Baseline results must use the 6809 instruction set; 6309
extensions belong in separately labeled comparisons.

## Current status

The shared **kr16** suite runs identical K&R-compatible sources under both
C3 (C-Cubed), CMOC, LLVM-MC6809 1.0, and vbcc on a bare-metal 6809 simulator. All four compilers are checked
with optimization disabled and enabled. All twelve shared benchmarks must match independent
reference results for four seeds before their sizes enter the comparison.

The original C89 suite remains available. CMOC runs it; C3's source-compatibility
limitations appear separately in collapsed diagnostics on the published page.
Executed instruction counts are measured for the shared suite. CPU cycle timing is not implemented yet.

## Run the checks

Requires a host C compiler, Make, and Python 3:

```sh
make check
```

Override `CC` and `CFLAGS` to check another host compiler or optimization level.
Run `make clean` when changing flags, since Make does not track flag changes.

| Benchmark | Work performed |
| --- | --- |
| crc16 | CRC-16/CCITT over bytes 0 through 255 |
| insertion_sort | Generate and sort 64 bytes; compute an ordered checksum |
| mix16 | 1,024 rounds of 16-bit shifts, XOR, and addition |

Benchmark functions use no I/O or allocation. The sort workload includes data generation
and checksum costs, including 32-bit arithmetic. Each benchmark function returns a checksum
for a supplied seed. Four seeds are checked against independent Python models.
The data model requires 8-bit bytes and 16-bit unsigned short; unsigned int
may be 16 or 32 bits. Historical dialect limitations should be recorded explicitly.

## GitHub Actions

The workflow builds and checks benchmark functions on pushes, pull requests, and manual
runs using host GCC/Clang and 6809 CMOC, each at `-O0` and `-O2`. CMOC 0.1.99
and LWTOOLS 4.24 are built from SHA-256-verified release archives. USIM is
built from the CMOC release. The two CMOC and two C3 jobs each record shared kr16 results as well as
the original-suite results. Together with four host reports, this produces
sixteen reports, including LLVM and vbcc at `-O0` and `-O2`. Host jobs also verify the kr16 algorithms.

## Comparison rules

- Compile the runner and benchmark function separately; disable link-time optimization.
- Verify output on the execution target before accepting measurements.
- Record the compiler version, exact commands, flags, source revision, ABI,
  platform, CPU, and emulator or hardware configuration.
- Measure cycles around `bench_run`, excluding runner I/O. Document call and
  timer overhead, interrupt handling, repetitions, and subtraction methods.
- Distinguish benchmark function code/data size, linked runtime size, and complete executable
  size. Include compiler helper routines in a documented size accounting method.
- Keep bare-metal and OS-9 comparisons separate. Compare matching optimization
  goals and publish all flags. Do not infer cycle counts from host elapsed time.

## Adding a 6809 toolchain

See [adapters/README.md](adapters/README.md) for the adapter contract and
[results/README.md](results/README.md) for required measurement metadata.
Start with one verified compiler/target combination, then add a second using
the same benchmark functions and measurement boundaries. Compiler binaries and ROM images
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
for an existing installation; LWTOOLS must also be on PATH. Each benchmark function and
runner are compiled separately. Each run has a 60-second timeout. Reports
include compiler/assembler/linker versions, exact command arguments, checksums,
and sizes. CI retains assembly, S-record executables, maps, and command logs.

CMOC has no `limits.h`; `bench.h` uses its documented 8-bit-byte data model
and a compile-time short-size check. The benchmark algorithms are unchanged.
The USIM adapter uses CMOC's `cmoc.h` for output.

Benchmark code size is the benchmark function object's `code` section, excluding linked
helpers. Complete test program size counts unique S-record data bytes, including
startup, runner, initialized data, and linked runtime, but excluding BSS and
S-record text overhead. These metrics are distinct and are not standalone
benchmark function footprint measurements. Timing is not measured by this adapter.

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
same benchmark function source; reports record SHA-256 hashes and the matrix rejects
mismatches. Assembly, objects, executables, maps, and command logs are retained.

`kr16` is a distinct workload variant, not a silent rewrite of the original
suite. It uses K&R definitions, `unsigned` arithmetic explicitly masked to
16 bits, and no standard headers. The sort stores values 0..255 in unsigned
words and uses 16-bit multiplication, whereas the original sorts bytes and
uses 32-bit arithmetic. Checksum expectations are the same, but size results
must only be compared within the same suite.

The shared assembly harness supplies each seed in D and on the stack to cover
C3 and CMOC calling conventions; the LLVM branch moves the argument and
return value through X, then prints the returned 16-bit checksum.
It loads at $2800 with stack top $FE00 and a reserved 4 KiB stack region; these
bounded benchmark functions use no static storage. C3's `_stkcheck` calls use a no-op stub,
so this is a bare-metal benchmark function comparison, not an OS-9 runtime comparison.
Only referenced compiler helper routines are linked. Ranked code size includes
those helpers and excludes the common harness; complete size includes both.

## LLVM-MC6809 release 1.0

[Release 1.0](https://github.com/markrvmurray/llvm-mc6809/releases/tag/RELEASE_1.0)
was the latest stable release when checked on November 19, 2026 (published
November 16). CI pins that release and its published SHA-256 archive checksums
rather than silently changing compilers on each run. The version banner records
LLVM clang 24.0.0 and compiler revision
`b9af0417885deb8e878ba50e59f90bb8037577f7`.

The installer supports Linux x86-64 (GitHub Actions) and macOS Apple silicon:

```sh
sh tools/build-cmoc.sh  # supplies the common USIM simulator
sh tools/install-llvm.sh
python3 tools/run-kr16.py --compiler llvm --optimization 0 --json build/reports/kr16-llvm-O0.json
python3 tools/run-kr16.py --compiler llvm --optimization 2 --json build/reports/kr16-llvm-O2.json
python3 tools/matrix.py build/reports build/site
```

The unchanged kr16 benchmark functions are compiled with `-mcpu=mc6809 -std=c89 -fno-pie
-fno-lto` and `-O0` or `-O2`. LLVM's integrated assembler and LLD produce ELF;
`mc6809-objcopy` converts it to S-records for the same USIM used by C3/CMOC.
Only referenced LLVM compiler-runtime and C-library helper routines are linked
(including `memmove` when LLVM recognizes a copy loop). No full C-library
startup, 6309 instructions, or link-time optimization is used.

The shared harness is translated to LLVM assembler directive/label syntax,
with a calling-convention branch for X as the first argument and return
register. This adds four bytes of register-transfer instructions to the
loaded harness; the benchmark function code metric excludes it. LLVM reserves 24 bytes
of direct-page scratch registers, mapped at $0000–$0017; those RAM bytes are
not counted as loaded code. ELF files, generated assembly, maps, and version
banners are retained in CI artifacts. Ranked code size counts loaded benchmark,
support, and runtime-helper bytes, including constants and initialized data,
minus the measured harness. It excludes BSS, metadata, and ELF headers.

`-O2` is a general optimization setting, not a size-minimizing setting. LLVM
unrolls the CRC loop at `-O2`, so its code can be larger than at `-O0`.
The matrix reports actual sizes without interpreting size as execution speed.

## Expanded shared test coverage

The kr16 suite contains 12 tests, each run with four seeds on all three
compilers at two optimization settings: **288 target checksum checks**.
Host GCC/Clang also check the shared sources. The original three C89 tests
remain a separate suite.

| Test | Main coverage |
| --- | --- |
| CRC16 | Shifts, XOR, nested loops |
| Insertion sort | Array indexing, comparisons, nested loops |
| 16-bit arithmetic | Repeated shifts, XOR, wraparound addition |
| Multiplication | Variable unsigned products and wraparound |
| Division and remainder | Unsigned quotient/remainder, varying nonzero divisors |
| Word copy | Pointer increments, copying, overlapping left shift |
| Binary search | Present/absent keys, comparisons, conditional branches |
| Switch dispatch | Eight state-dependent cases |
| Function calls | Three arguments and a separately compiled callee |
| Recursive GCD | Recursion, remainder, separate translation units |
| Signed arithmetic | Signed comparisons and bounded additions/subtractions |
| Linked structures | Structure layout, fields, pointer traversal |

`tools/shared_suite.py` owns the inventory, descriptions, and independent
Python reference calculations. Search uses a direct expected-index formula;
GCD uses Python's `math.gcd`; the pointer tests use Python sequences and
index arithmetic rather than reproducing C pointer operations.

Supporting functions are compiled separately without LTO. Their code counts
toward ranked code size along with linked compiler/library helpers. Report hashes cover every source file for a test. The runtime
error hook stops USIM with a nonzero status if a C3 arithmetic helper reports
an error; it does not silently return success.

Comparison tables group optimization On/Off subrows beneath one linked benchmark
name. Expand **Test purposes and source files** for descriptions, supporting
functions, and the original C89 suite. Links point to the exact Git commit used by CI. Local previews without a commit ID use `main`.

### Failure discovered by the expanded suite

The pinned C3 compiler built with GCC on GitHub's Linux runner crashes with
exit 139 while compiling `list16.c`, before its target-code optimizer runs.
Both optimizer configurations expose it. The same source compiles and executes
correctly with the locally built C3 on macOS; CMOC and LLVM pass it on both
hosts. This identifies a host-dependent C3 compilation failure, not a runtime
checksum failure. The underlying compiler defect has not been diagnosed.
The report retains the failure and excludes its size; CI correctly flags the
C3 jobs. Source, commands, and diagnostics are preserved for investigation.


## vbcc 6809

The [author's 6809 Release 1 Preview dated 2026-01-25](http://www.compilers.de/vbcc6809_20260125.zip)
is pinned by SHA-256 in `tools/install-vbcc.sh`. GitHub Actions installs the
bundled Linux x86_64 compiler, vasm, vlink, and runtime library. The archive's
vbcc manual contains the upstream license terms; toolchains are downloaded
at build time rather than vendored into this repository.

```sh
sh tools/install-vbcc.sh
python3 tools/run-kr16.py --compiler vbcc --optimization 0 --json build/reports/kr16-vbcc-O0.json
python3 tools/run-kr16.py --compiler vbcc --optimization 2 --json build/reports/kr16-vbcc-O2.json
```

The compiler uses `-cpu=6809` and `-O=0` or `-O=1023` (the compiler optimization
mask selected by `vc -O2`). Sources are compiled separately without whole-program
optimization. Both configurations use vasm's standard branch and offset relaxation.
The same USIM harness passes the first argument and result in D. vlink emits
S-records at address `$2800`; only referenced helpers from the supplied `libvc.a`
are linked. Ranked code size includes test objects, supporting functions, and
linked runtime helpers, excluding the measured harness. Complete program size
adds the harness back in. These are bare-metal USIM binaries, not OS-9 modules.

For native macOS testing, build `vbcchc12` with `TARGET=hc12` from the bundled
`vbcc.tar.gz`, and `vasm6809_std` with `CPU=6809 SYNTAX=std` from `vasm.tar.gz`.
Place those binaries and a native vlink in `build/vbcc/bin`, and copy the bundled
`targets` directory to `build/vbcc/targets`. Native linker versions are recorded
in reports; CI uses the complete pinned Linux distribution.

The optimized build currently fails `signed16`: seed `0` returns `$91B2`
instead of `$ED62`. All four seeds disagree. The unoptimized build passes;
the report excludes the failing optimized result from size rankings. The
cause has not yet been isolated to compiler code generation or a runtime helper.


### Overall code-size ranking

The report ranks compilers separately with optimization on and off. It uses
only tests where all four compilers pass and report a positive benchmark-code
size. For each included test, each compiler's size is divided by that test's
smallest size. The geometric mean of those ratios gives every test equal
weight; scores are then scaled so the leading compiler has an index of 100.
An index of 120 means a geometric-mean size ratio 20% above the leader.
Ties share a place at two-decimal precision. Total bytes and full-suite pass
counts appear alongside the score; exclusions are listed for each setting.
Ranked `code_bytes` is the unique loaded S-record byte count minus the exact
harness range (`start` to `harness_end`) measured from each linker map. This
includes all linked runtime helpers, constants, and initialized data, while
excluding the harness and BSS. `harness_bytes` records the subtraction;
`kernel_code_bytes` retains the older test-object-only number for diagnostics
and is no longer used for shared-suite rankings. Original C89 detail rows keep
their explicitly labeled historical function-only metric and are not ranked.
For example, optimized LLVM `mul16` scores 73 bytes: 39 for the function plus
34 for `__mulhi3`, excluding its 113-byte harness. This ranking describes this
benchmark suite, not general compiler correctness or all C workloads.


### Executed instruction counts

The shared suite records instructions executed in USIM for each of the four
seeds and their sum. A small opt-in patch to the pinned CMOC USIM source counts
one instruction per CPU execution step; a prefixed opcode still counts as one.
Each build checks the counter against a hand-counted assembly program: two
calls of exactly 11 instructions, including a loop, subroutine, and prefixed LDY.

Exported `bench_begin`/`bench_end` labels delimit the measurement without adding
any target instructions or changing binary size. The range includes the call,
return, LLVM's ABI register transfers, all benchmark support functions, and
linked runtime helpers (including C3's no-op stack-check RTS). It excludes startup,
loading the seed, printing results, and the harness's argument-stack cleanup.
Linker maps supply the boundary addresses for each compiler. During counted
bare-metal runs USIM's host-clock IRQ trigger is disabled for deterministic results.

The report shows the total across all four seeds; `instructions_by_seed` in
raw JSON and `*.instructions.log` artifacts preserve individual measurements.
A missing or incomplete counter is an error, never a zero measurement. Incorrect
results retain their diagnostic counts in raw data but are excluded from report
rankings. Original C89/host probes do not have instruction counts.

Instruction count is **not cycle count**: addressing modes, branches, and other
6809 operations have different cycle costs. Accurate cycles would require a
validated cycle-accounting implementation in the simulator, including indexed
addressing and taken-branch penalties; host elapsed time is not a substitute.


### Assembly linked from size measurements

Click any individual benchmark or complete-program size in the HTML or Markdown
matrix to compare all four compilers' generated assembly side by side for that
test and optimizer setting. Matching source files align across columns, with
independently scrollable assembly panes and explicit failed-build diagnostics.
Each page includes all test compilation units (including support functions),
compiler version, source revision, and linker map. C3's optimized view retains the
output of `c3optx`; the other compilers retain their `.s` assembler inputs.
These pages contain compiler output rather than a disassembly of linked library
helpers. The linker map identifies those helpers included in the ranked size.

Assembly and maps travel in the report JSON, so GitHub Pages publishes them with
the matching measurements; they do not depend on the retention of Actions artifacts.
The site reflects the latest run, while each downloadable matrix artifact preserves
its own assembly pages. Failed measurements do not receive numeric size links.
