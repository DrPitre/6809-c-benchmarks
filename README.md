# 6809 C compiler benchmarks

A starter suite for comparing C compilers targeting the Motorola 6809.
The CoCo is one possible execution platform, alongside OS-9 and other
6809 systems. Baseline results must use the 6809 instruction set; 6309
extensions belong in separately labeled comparisons.

## Current status

The shared **kr16** suite runs identical K&R-compatible sources under
C3 (C-Cubed), CMOC, LLVM-MC6809 1.1.0-rc2, vbcc, and JKBert/gcc6809 on a bare-metal 6809 simulator. All five compilers are checked
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
runs using host GCC/Clang and 6809 CMOC, each at `-O0` and `-O2`. CMOC 0.1.101
and LWTOOLS 4.24 are built from SHA-256-verified release archives. USIM is built separately from the pinned
[markrvmurray/usim](https://github.com/markrvmurray/usim) revision in
`tools/usim-revision.txt`. The two CMOC and two C3 jobs each record shared kr16 results as well as
the original-suite results. Together with four host reports, this produces
twenty kernel/compatibility reports and one application report, including LLVM, vbcc, and gcc6809 at `-O0` and `-O2`,
plus LLVM at `-Os` and `-Oz`. Host jobs also verify the kr16 algorithms.

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

The landing page has three focused views: **Smallest code**, **Fewest
instructions**, and **Size versus execution**. Each ranks compiler-and-flags
configurations together, including LLVM `-O2`, `-Os`, and `-Oz`. Optimized
configurations are shown first; per-test assembly links, unoptimized builds,
versions, and historical runs are collapsed. Full on/off tables, compatibility
checks, and detailed methodology remain on `details.html`, with a complete
Markdown version in `details.md`. `matrix.md` is the compact summary.

Size and instruction indices give each benchmark equal weight. All optimized
configurations use the same intersection of tests with valid passing metrics.
The tradeoff view has no combined score: it highlights configurations that
are not dominated on the two indices. Instruction count is not cycle timing.

The page shows the benchmark workflow's start date and time in Eastern time,
with a link to the run. The same timestamp is saved in `results.json`, so
regenerating the page does not change the run date. Historical reports without
a recorded timestamp say so explicitly.

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

C3 comes from [nitros9-languages](https://github.com/nitros9project/nitros9-languages/tree/81120bb5bd9dd2d2d221a527af33f980108a26ed/c3),
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
Only required compiler runtime archive members are linked. Ranked code size includes
those helpers and excludes the common harness; complete size includes both.

## LLVM-MC6809 1.1.0-rc2

[Release 1.1.0-rc2](https://github.com/markrvmurray/llvm-mc6809/releases/tag/RELEASE_1.1.0_rc2)
is a **prerelease**, published November 24, 2026. CI pins this exact candidate
and its published SHA-256 archive checksums. The version banner records LLVM
clang 24.0.0 and compiler revision
`19fc4dc208bed7d29e31eeeac21edf177fec5fb6`.

The published RC1 results are preserved in `history/llvm-1.1.0-rc1/results.json`,
with their original simulator provenance and workflow start time. The site
links that historical report. RC2's release notes describe unchanged compiler
code generation; the benchmark rerun checks its actual sizes and instructions.

The preceding five-compiler results are preserved in
`history/llvm-1.0/results.json`, with checksums, assembly, maps, source hashes,
and instruction counts. The generated site links a separate historical report
labeled LLVM-MC6809 1.0. The older CMOC snapshot also remains available. New
installations replace the entire LLVM bundle and retain any previous directory
under `build/llvm-previous.*`, avoiding mixed runtime files from different releases.

The installer supports Linux x86-64 (GitHub Actions) and macOS Apple silicon:

```sh
sh tools/build-cmoc.sh  # supplies the common USIM simulator
sh tools/install-llvm.sh
python3 tools/run-kr16.py --compiler llvm --optimization 0 --json build/reports/kr16-llvm-O0.json
python3 tools/run-kr16.py --compiler llvm --optimization 2 --json build/reports/kr16-llvm-O2.json
python3 tools/run-kr16.py --compiler llvm --optimization s --json build/reports/kr16-llvm-Os.json
python3 tools/run-kr16.py --compiler llvm --optimization z --json build/reports/kr16-llvm-Oz.json
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

`-O2` is a general optimization setting. The detailed report’s **LLVM size optimization
versus vbcc** section compares LLVM `-O2`, `-Os`, and `-Oz` with vbcc `-O=1023`
(`vc -O2`). It includes normalized size rankings, total code plus helpers,
per-test sizes and instruction counts, correctness, and four-way assembly
comparisons. The detailed five-compiler on/off rankings retain LLVM `-O2` and
`-O0`; size modes never replace those measurements. All three LLVM optimized
configurations receive identical sources, ABI, libraries, and harnesses.
Smaller-size optimization requests do not guarantee smaller final programs:
linked helper choices and backend decisions also contribute.

## Expanded shared test coverage

The kr16 suite contains 12 tests, each run with four seeds on all five
compilers at two optimization settings: **480 target checksum checks**.
The two additional LLVM size modes add **96 target checksum checks**, for
**576** across all recorded shared configurations.
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

### C3 structure-declaration fix

The C3 pin includes upstream PR #18, which initializes `settype`'s dimension
output before its structure-tag early returns. This fixes the host-dependent
`list16.c` compiler crash without changing the shared benchmark sources.
The fix is present in `comp`, `compexp`, and `compexpansi`; upstream regression
checks cover single-pass, two-pass, and experimental compilation. The benchmark
uses the merged upstream revision directly, without a local compiler patch.


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

The earlier optimized `signed16` failure came from the old CMOC-bundled
USIM's inverted `NEG` carry/borrow flag. The benchmark now uses the unmodified
6809 CPU core from `markrvmurray/usim`, which implements NEG correctly. No local
CPU patch is applied. The build checks all 256 byte inputs in five NEG forms
(result and N/Z/V/C), plus all 65,536 inputs to vbcc's 16-bit negation sequence.
Historical reports retain their original measurements and simulator provenance.


## JKBert/gcc6809

[JKBert/gcc6809](https://github.com/JKBert/gcc6809) is a new GNU backend,
separate from the older gcc6809 project. Its GitHub repository contains build
recipes; the author distributes the patched GCC, binutils, and newlib sources
on an OpenVMS FTP server. `tools/gcc6809-sources.json` pins the November 10,
2026 archives and their SHA-256 hashes. Builds prefer byte-identical HTTPS
mirrors in this repository’s `gcc6809-sources-20261110` release, with the author’s
FTP URLs retained as fallback and provenance. Downloads must match the same
pinned hashes before extraction; archived host build outputs are removed
before compiling. This avoids FTP connectivity failures on hosted runners.

On Ubuntu, install `build-essential bison flex curl libgmp-dev libmpfr-dev
libmpc-dev texinfo`, then:

```sh
sh tools/build-gcc6809.sh
sh tools/build-cmoc.sh  # supplies the common USIM simulator
python3 tools/run-kr16.py --compiler gcc6809 --optimization 0 --json build/reports/kr16-gcc6809-O0.json
python3 tools/run-kr16.py --compiler gcc6809 --optimization 2 --json build/reports/kr16-gcc6809-O2.json
python3 tools/matrix.py build/reports build/site
```

By default, compiler sources live under `~/Projects/gcc6809/sources`, alongside
an existing clone of the build-recipe repository. `GCC6809_SOURCE_DIR` overrides
that location; CI uses `build/sources/gcc6809`. Installed tools and build outputs
stay under `build/gcc6809` and `build/gcc6809-build`. Set `GCC6809_PREFIX` to use
another installation. On macOS, install the GMP, MPFR, MPC, and GNU build
prerequisites first; `GCC6809_HOST_PREFIX` can point to a common prefix containing
those three libraries. The installer preserves existing source directories
that it did not create and asks for an empty source destination.

Only the C frontend, plain 6809 binutils, newlib, and libgcc are needed. The
build disables multilib; no 6309 or 63F09 results enter this comparison. Each
unchanged kr16 translation unit is compiled separately with `-m6809 -std=gnu89
-fno-pie -fno-lto` and `-O0` or `-O2`. Arguments are passed on the stack and
16-bit results return in D. The common harness already supplies that stack
argument, so no extra ABI instructions are needed. A native Apple silicon
macOS build of this pinned snapshot passed all 96 shared-suite checksum checks
across both settings on November 22, 2026.

The GNU linker uses `adapters/kr16-gcc6809.ld` at `$2800`; objcopy converts ELF
to S-records for the same USIM. Only referenced newlib/libgcc archive members
are linked, with no library startup. GNU runtime assembly can group several
functions in one archive member; every loaded byte of that member counts.
The linker rejects BSS (the common harness
does not initialize it) and programs overlapping the reserved stack. Size
accounting includes all loaded helpers and constants and subtracts the exact
harness range from the GNU linker map. Generated assembly, maps, commands,
source hashes, compiler versions, and per-seed instruction counts use the
same report format as the other compilers. CI builds the GNU toolchain once
and runs both optimization settings; incorrect or unbuildable results remain
visible and never enter rankings. Reports containing gcc6809 use five columns;
the preserved four-compiler reports retain their original comparison group.

### Overall code-size ranking

The report ranks compilers separately with optimization on and off. It uses
only tests where all participating compilers pass and report a positive benchmark-code
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
seeds and their sum. The benchmark machine adapter uses the pinned CPU's `pre_exec` hook to count
one instruction per CPU execution step; a prefixed opcode still counts as one.
Each build checks the counter against a hand-counted assembly program: two
calls of exactly 11 instructions, including a loop, subroutine, and prefixed LDY.

Exported `bench_begin`/`bench_end` labels delimit the measurement without adding
any target instructions or changing binary size. The range includes the call,
return, LLVM's ABI register transfers, all benchmark support functions, and
linked runtime helpers (including C3's no-op stack-check RTS). It excludes startup,
loading the seed, printing results, and the harness's argument-stack cleanup.
Linker maps supply the boundary addresses for each compiler. The adapter attaches no interrupt-producing devices, so bare-metal runs are
deterministic.

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
matrix to compare all participating compilers' generated assembly side by side for that
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


### Preserving compiler releases

The current matrix uses CMOC **0.1.101**, pinned to its official release archive
and SHA-256. The published CMOC 0.1.99-era results are frozen in
`history/cmoc-0.1.99/results.json`, including assembly, maps, source hashes,
instruction counts, and the other compilers' contemporary results.
`snapshot.json` records the original Git revision, workflow run, and file digest.
The site rebuilds a separate historical report with its original measurements,
rankings, source links, and assembly pages; updating a compiler does not replace
that snapshot. The historical report is clearly labeled and links back to the
current report.

The current report includes a CMOC 0.1.99 → 0.1.101 table for both optimization
settings. Negative deltas mean smaller code or fewer instructions. It computes
deltas only for passing tests with identical source hashes and harness sizes;
the comparison lists only test/settings with a nonzero byte or instruction delta.
Each benchmark name links to old/new CMOC assembly side by side with added,
removed, and changed text highlighted. Unchanged and noncomparable rows are
omitted. Full measurements remain accessible in the current and preserved reports.
The main current-compiler rankings use the current release only.

USIM is pinned independently of CMOC using `tools/usim-revision.txt` and
`tools/build-usim.sh`. Changing the CMOC version does not change the simulator.
The adapter preserves the suite's `$FF00` console, `SYNC` exit convention,
S-record entry points, and instruction boundaries without changing target
binaries. Reports record the simulator revision and adapter SHA-256. The
historical CMOC 0.1.99 snapshot retains its original bundled-USIM provenance. To reproduce the earlier compiler build:

```sh
CMOC_VERSION=0.1.99 sh tools/build-cmoc.sh
```

Running the build script without that override installs 0.1.101. Both source
archive checksums remain pinned in the script.

## Real NitrOS-9 applications

A separate [application comparison](https://drpitre.github.io/6809-c-benchmarks/applications.html)
builds `uniq`, `dgrep` and `ed` from pinned nitros9-apps sources. Eight configurations
(C3 off/on, LLVM O0/O2/Os/Oz, vbcc O0/O2) execute 27 fixtures each under a real
NitrOS-9 Level 2 kernel in Pico-Thing USIM. Complete module sizes include startup,
linked libraries, headers and CRC. Only programs passing all their output checks
receive a size result; application results never enter bare-metal rankings.

After the existing CMOC/LWTOOLS, C3, LLVM and vbcc installation scripts, run:

```sh
# Linux prerequisites additionally include libsdl2-dev, pkg-config and zlib1g-dev.
python3 tools/build-os9-apps.py
python3 tools/run-os9-apps.py --json reports/os9-apps.json
```

`tools/os9-app-sources.json` pins the application, kernel, ToolShed and video
sources; the existing USIM pin also governs the full-machine emulator. The test
image uses standard Shell edition 22 rather than Shell+, avoiding interpretation
of regex characters as extended shell operators. A fixed build epoch controls
kernel disk metadata; the report records the actual workflow run date separately.

Every compiler receives the same `benchmarks/os9-apps/portable.patch`, which fixes
legacy declarations, the invalid fopen failure check, and dgrep's end anchor at
the newline retained by fgets. Inputs use native CR line endings. Output checks
normalize line endings only and preserve all other bytes. Fixtures cover short,
terminated ASCII lines; long lines and unterminated input are outside this suite.

C3 and LLVM RC2 with the pinned OS-9 runtime fix pass every fixture. vbcc
passes uniq/dgrep and six of eight ed cases. The pinned preview drops a 256-byte
automatic-array pointer offset, breaking ed substitution. Its two failing ed
rows stay FAIL and receive no size result; see `benchmarks/os9-apps/vbcc-ed-offset.c`.
CI opts into accepting only the exact recorded output/file failures with
`--allow-vbcc-ed-offset-bug`. Other output differences, failed builds, failed
runtime probes or failing fixtures still fail the job. The runner is strict
without this flag.
The LLVM compiler remains the released RC2 binary. `tools/llvm-os9-runtime.json`
pins the picolibc source fix; `tools/install-llvm.sh` rebuilds its default 6809
integer OS-9 C library with Meson 1.11.2. Other bundled targets and variants
remain the release libraries. Building this overlay requires Git, Ninja and
Python pip in addition to the existing release installer prerequisites.

The runtime converts CR to C newline on input and C newline to CR on output
for descriptor-backed text streams. Binary modes, raw POSIX reads/writes and
memory/cookie streams retain every byte. A separate on-target runtime regression
checks all 256 byte values, small buffers, line buffering, EOF, seeks, ungetc,
fdopen, freopen and exact CR output on redirected stdin/stdout/stderr. CI runs
this regression and the O2 application cases with `fast-bufio=true`, then
rebuilds the default library before the complete comparison. Runtime source,
options and library digest are recorded in `build/llvm/OS9-RUNTIME.json` and
in the application report. This suite measures complete program size, not execution speed or peak
RAM. Requested data is the module header allocation request. CMOC and gcc6809
await suitable OS-9 stdio/runtime integration before entering this comparison.
The runner exits nonzero for application or runtime regression failures; CI retains
the evidence and reports failures so they cannot silently become size winners.

ed fixtures cover append/print, global substitution, deletion, insertion,
move, global matching, native CR file input, and save/reopen. The saved file
must match native CR bytes exactly, in addition to matching stdout. Each run
uses private fixture/output filenames per compiler configuration. Every ed C
and header file is fingerprinted, and all 37 translation units are linked with
each compiler's own runtime. The common patch supplies missing declarations
and fixes the signal-handler return type; only C3 defines `BENCH_C3` to retain
its explicit `pflinit` call. Interactive signal handling and unexercised editor
commands are outside this scripted comparison.
