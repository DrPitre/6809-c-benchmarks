#include "bench.h"
/* Defined modulo-65536 shifts, addition, and XOR. */
unsigned short bench_run(unsigned short seed)
{
    unsigned short state;
    unsigned int i;
    state = seed;
    for (i = 0; i < 1024; ++i) {
        state = (unsigned short)(state ^ (unsigned short)(state << 7));
        state = (unsigned short)(state ^ (state >> 9));
        state = (unsigned short)(state + 0x9e37U);
    }
    return state;
}
