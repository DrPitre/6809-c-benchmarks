#ifndef BENCH_H
#define BENCH_H
#ifdef _CMOC_VERSION_
/* CMOC has no limits.h; its documented data model has 8-bit bytes. */
typedef char bench_short_must_be_16_bits[sizeof(unsigned short) == 2 ? 1 : -1];
#else
#include <limits.h>
#if UCHAR_MAX != 255 || USHRT_MAX != 65535
#error Benchmarks require 8-bit unsigned char and 16-bit unsigned short
#endif
#endif
/* Separate compilation keeps the input unknown to the benchmark compiler.
 * Do not enable link-time optimization for baseline measurements. */
unsigned short bench_run(unsigned short seed);
#endif
