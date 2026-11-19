/* Variable 16-bit multiplication with explicit wraparound. */
unsigned bench_run(seed)
unsigned seed;
{
    unsigned i, a, b, sum;
    a = seed;
    b = 257;
    sum = 0;
    for (i = 0; i < 256; ++i) {
        a = (a + 4051) & 0xffff;
        b = (b + 257) & 0xffff;
        sum = (sum + ((a * b) & 0xffff)) & 0xffff;
    }
    return sum;
}
