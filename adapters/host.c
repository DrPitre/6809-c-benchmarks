#include <stdio.h>
#include "bench.h"
int main(void)
{
    static const unsigned short seeds[] = { 0U, 1U, 0x1234U, 0xffffU };
    unsigned int i;
    for (i = 0; i < sizeof(seeds) / sizeof(seeds[0]); ++i)
        printf("%u %u\n", (unsigned int)seeds[i],
               (unsigned int)bench_run(seeds[i]));
    return 0;
}
