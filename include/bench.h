#ifndef BENCH_H
#define BENCH_H
#include <limits.h>
#if UCHAR_MAX != 255 || USHRT_MAX != 65535
#error Benchmarks require 8-bit unsigned char and 16-bit unsigned short
#endif
/* Separate compilation keeps the input unknown to the benchmark compiler.
 * Do not enable link-time optimization for baseline measurements. */
unsigned short bench_run(unsigned short seed);
#endif
