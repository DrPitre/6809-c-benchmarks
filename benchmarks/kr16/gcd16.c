/* Recursion and unsigned remainder, through a separate translation unit. */
unsigned gcdcalc();
unsigned bench_run(seed)
unsigned seed;
{
    unsigned i, a, b, sum;
    sum = 0;
    for (i = 0; i < 64; ++i) {
        a = (seed + i * 257) & 0xffff;
        b = i * 37 + 1;
        sum = (sum + gcdcalc(a, b)) & 0xffff;
    }
    return sum;
}
