/* Signed comparisons and arithmetic, kept safely within -4000..4000. */
unsigned bench_run(seed)
unsigned seed;
{
    int value, delta, i;
    unsigned sum;
    value = (int)(seed & 2047) - 1024;
    sum = 0;
    for (i = 0; i < 128; ++i) {
        delta = ((i * 37) % 101) - 50;
        if (value < 0)
            value = value + 97 + delta;
        else
            value = value - 89 - delta;
        sum = (sum + ((unsigned)value & 0xffff)) & 0xffff;
    }
    return sum;
}
