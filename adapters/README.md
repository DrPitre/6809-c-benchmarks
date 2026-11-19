# Compiler and execution adapters

`host.c` is a correctness-only runner. A future target adapter should:

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
