# Results

No 6809 measurements have been collected yet.

Each published run should include:

- Source commit and any uncommitted patch
- Compiler identity/version and exact build/link commands
- Optimization goal, flags, CPU instruction set, ABI, and data model
- Platform (for example bare-metal CoCo or OS-9), startup and runtime versions
- Hardware clock/configuration or emulator version/configuration
- Benchmark name, seed, expected checksum, observed checksum, correctness status
- Cycles, measurement boundaries, overhead treatment, and repetition count
- Kernel code bytes, initialized data bytes, BSS bytes, linked helper/runtime
  bytes, executable bytes, and the method used to obtain each size
- Raw output and supporting map/listing artifacts

Use an explicit unavailable value for missing metrics, never zero. Publish
correctness failures, but exclude failed runs from performance rankings.
