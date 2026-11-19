#include <stdio.h>
unsigned bench_run(unsigned seed);
int main(void)
{
    unsigned seeds[4];
    int i;
    seeds[0] = 0;
    seeds[1] = 1;
    seeds[2] = 0x1234;
    seeds[3] = 0xffff;
    for (i = 0; i < 4; ++i)
        printf("%u %u\n", seeds[i], bench_run(seeds[i]));
    return 0;
}
