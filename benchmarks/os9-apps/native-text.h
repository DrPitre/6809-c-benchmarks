#ifndef BENCH_NATIVE_TEXT_H
#define BENCH_NATIVE_TEXT_H
/* cmoc_os9 exposes native CR text input. Other runtimes/compiler character
 * conventions already make their input terminator agree with '\n'. */
#ifdef BENCH_CMOC
#define BENCH_NL '\r'
#define BENCH_EOL "\r"
#define BENCH_TEXT(lf, cr) cr
#else
#define BENCH_NL '\n'
#define BENCH_EOL "\n"
#define BENCH_TEXT(lf, cr) lf
#endif
#endif
