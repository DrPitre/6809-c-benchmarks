/* Pointer-based word copy, followed by an overlapping left shift. */
unsigned bench_run(seed)
unsigned seed;
{
    unsigned src[64], dst[64];
    unsigned *p, *q, i, state, sum;
    state = seed;
    for (i = 0; i < 64; ++i) {
        state = (state * 109 + 89) & 0xffff;
        src[i] = state;
    }
    p = src;
    q = dst;
    for (i = 0; i < 64; ++i)
        *q++ = *p++;
    p = dst + 1;
    q = dst;
    for (i = 0; i < 63; ++i)
        *q++ = *p++;
    sum = 0;
    for (i = 0; i < 64; ++i)
        sum = (sum + (dst[i] ^ (i * 257))) & 0xffff;
    return sum;
}
