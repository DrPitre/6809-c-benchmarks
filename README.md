# 6809 C compiler benchmarks

A starter suite for comparing C compilers targeting the Motorola 6809.
The CoCo is one possible execution platform, alongside OS-9 and other
6809 systems. Baseline results must use the 6809 instruction set; 6309
extensions belong in separately labeled comparisons.

## Current status

Three C89 kernels and a host correctness runner are implemented. No 6809
compiler adapter or performance results are included yet. Host runs validate
semantics only: they do not establish 6809 compatibility, speed, or code size.

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

The included workflow runs `make check` on pushes, pull requests, and manual
runs, using GCC and Clang at both `-O0` and `-O2`. These jobs validate host
correctness. Actual 6809 measurements will require installing a target compiler
and emulator in CI, with pinned versions and reproducible configurations.

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
downloadable `benchmark-matrix` artifact. Main-branch runs deploy the HTML and
Markdown report to GitHub Pages. Enable **Settings → Pages → Build and deployment
→ Source → GitHub Actions** after publishing this repository to GitHub.

The deployment follows the [GitHub Pages custom workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

To preview a local report:

```sh
make check
BENCH_CC=cc BENCH_FLAGS=-O2 python3 tools/check.py --json build/reports/local.json
python3 tools/matrix.py build/reports build/site
```

Open `build/site/index.html`. Local results describe only the compiler and flags
you actually used; set the metadata variables accordingly.
