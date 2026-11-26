# Compiler and execution adapters

`host.c` is a host correctness runner. `cmoc-usim.c` runs the same seed set
using CMOC output routines on USIM. `tools/run-cmoc.py` builds it and collects
correctness and sizes; `tools/build-cmoc.sh` builds pinned dependencies.

Additional target adapters should:

1. Document toolchain installation prerequisites and supported C dialect.
2. Compile each unchanged benchmark function separately from its platform runner.
3. Run all four seeds used in `tools/check.py` and compare checksums.
4. Provide reproducible commands for building and executing artifacts.
5. Measure the complete `bench_run` call with a documented cycle-count boundary.
6. Save map/listing files where supported and explain size accounting.

Keep compiler configuration distinct from platform execution support: the same
compiler may support several environments. Target-specific startup, output, and
timing belong here, not in the benchmark functions. Never silently rewrite a benchmark function to make
one compiler accept it; record a compatibility failure or publish a separately
named variant. Capability probes and library coverage are future additions.

`tools/run-c3.py` is a compile-compatibility adapter for pinned C-Cubed. It
links a smoke OS-9 module, then records source acceptance with the optimizer
on and off. It does not execute modules or collect benchmark sizes. See the
main README for the observed dialect limitations and status meanings.

`tools/run-kr16.py` executes identical sources from `benchmarks/kr16/` with
C3, CMOC, and LLVM-MC6809. `kr16-usim.asm` and `kr16-usim.link` provide a common
bare-metal harness, changing only the imported benchmark function symbol for the compiler
ABI. C3 objects are translated by its upstream `c3-as`; helper routines come
from its `libc3lw` archive. CMOC uses its own helper archives. All are run by
the same pinned USIM executable. The source hash is part of every result.

This harness deliberately supports benchmark functions without static storage, OS calls,
or floating point. Do not use it as a general OS-9 loader. `_stkcheck` is a
no-op stub for the bounded stack usage of these benchmark functions. The full C3 OS-9
runtime is not part of these results.

LLVM uses `kr16-llvm.ld` with ELF objects and compiler-runtime helpers from
the pinned LLVM release. The harness is translated from the common assembly source to
LLVM directive syntax; the `LLVM_ABI` branch transfers the seed/result via X.
Its 24-byte direct-page register area follows the release's picolibc linker
layout. No operating-system startup or library runner is linked.

The shared inventory includes separately compiled call and recursion support
functions. The adapter links all test objects and includes their code in the
benchmark-code metric. C3's `_rpterr` hook terminates the simulator with a
nonzero result. LLVM can emit C-library calls such as `memmove`; referenced
picolibc routines are linked and counted in complete-program size.

`gcc6809` uses GNU ELF objects with `kr16-gcc6809.ld` and the common harness's
undecorated `bench_run` symbol. Its plain 6809 ABI takes arguments on the stack
and returns 16-bit results in D. GNU objcopy emits S-records; GNU linker-map
symbols supply the same size and instruction-count boundaries. The adapter
links referenced libgcc/newlib helpers without startup, rejects uninitialized
storage, and reserves the same 4 KiB stack. Sources are built by
`tools/build-gcc6809.sh`; see the main README for source and install locations.

## Pinned USIM machine

`tools/build-usim.sh` fetches the exact `markrvmurray/usim` commit in
`tools/usim-revision.txt` and compiles its unmodified 6809 core with
`usim-bench.cpp`. C++20 is required. No Pico-Thing firmware, SDL, 6309 core,
or CPU-source patches are needed.

The machine provides 64 KiB RAM, a byte console at `$FF00`, and successful
exit only for `SYNC` with D=0. It validates 16-bit S-record checksums and uses
the S9 entry point. Invalid opcodes, malformed inputs, incomplete measurements,
and the default 100-million-instruction limit fail the run. Override the cap
with `USIM_MAX_INSTRUCTIONS`. Measurement boundaries use `USIM_BENCH_BEGIN` and
`USIM_BENCH_END` hexadecimal addresses; the upstream pre-execution hook counts
instructions between them. No target code or harness byte counts change.

The build checks the hand-counted measurement fixture and exhaustive NEG
behavior. Existing reports retain their old simulator metadata. New reports
record the CPU commit and the machine adapter's SHA-256.
