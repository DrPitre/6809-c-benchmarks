# Compiler and execution adapters

`host.c` is a host correctness runner. `cmoc-usim.c` runs the same seed set
using CMOC output routines on USIM. `tools/run-cmoc.py` builds it and collects
correctness and sizes; `tools/build-cmoc.sh` builds pinned dependencies.

Additional target adapters should:

1. Document toolchain installation prerequisites and supported C dialect.
2. Compile each unchanged kernel separately from its platform runner.
3. Run all four seeds used in `tools/check.py` and compare checksums.
4. Provide reproducible commands for building and executing artifacts.
5. Measure the complete `bench_run` call with a documented cycle-count boundary.
6. Save map/listing files where supported and explain size accounting.

Keep compiler configuration distinct from platform execution support: the same
compiler may support several environments. Target-specific startup, output, and
timing belong here, not in the kernels. Never silently rewrite a kernel to make
one compiler accept it; record a compatibility failure or publish a separately
named variant. Capability probes and library coverage are future additions.

`tools/run-c3.py` is a compile-compatibility adapter for pinned C-Cubed. It
links a smoke OS-9 module, then records source acceptance with the optimizer
on and off. It does not execute modules or collect benchmark sizes. See the
main README for the observed dialect limitations and status meanings.

`tools/run-kr16.py` executes identical sources from `benchmarks/kr16/` with
both C3 and CMOC. `kr16-usim.asm` and `kr16-usim.link` provide a common
bare-metal harness, changing only the imported kernel symbol for the compiler
ABI. C3 objects are translated by its upstream `c3-as`; helper routines come
from its `libc3lw` archive. CMOC uses its own helper archives. Both are run by
the same pinned USIM executable. The source hash is part of every result.

This harness deliberately supports kernels without static storage, OS calls,
or floating point. Do not use it as a general OS-9 loader. `_stkcheck` is a
no-op stub for the bounded stack usage of these kernels. The full C3 OS-9
runtime is not part of these results.
