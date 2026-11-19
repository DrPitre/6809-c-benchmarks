/* Defined modulo-65536 shifts, addition, and XOR. */
unsigned bench_run(seed)
unsigned seed;
{
    unsigned state;
    unsigned i;
    state = seed;
    for (i = 0; i < 1024; ++i) {
        state = (unsigned)(state ^ ((state << 7) & 0xffff));
        state = (unsigned)(state ^ (state >> 9));
        state = ((state + 0x9e37) & 0xffff);
    }
    return state;
}
