/* Three-argument calls to a separately compiled function; no LTO. */
unsigned step3();
unsigned bench_run(seed)
unsigned seed;
{
    unsigned state, i;
    state = seed;
    for (i = 0; i < 128; ++i)
        state = step3(state, i + 1, (seed ^ (i * 257)) & 0xffff);
    return state;
}
