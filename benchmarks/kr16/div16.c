/* Unsigned division/remainder; divisor is always 1..255. */
unsigned bench_run(seed)
unsigned seed;
{
    unsigned i, value, divisor, sum;
    value = seed;
    sum = 0;
    for (i = 0; i < 192; ++i) {
        value = (value + 4051) & 0xffff;
        divisor = ((i * 37 + (seed & 255)) % 255) + 1;
        sum = (sum + value / divisor + (value % divisor) * 17) & 0xffff;
    }
    return sum;
}
