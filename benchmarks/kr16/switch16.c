/* Eight-way dispatch driven by changing unsigned state. */
unsigned bench_run(seed)
unsigned seed;
{
    unsigned state, i;
    state = seed;
    for (i = 0; i < 256; ++i) {
        switch ((state ^ i) & 7) {
        case 0: state = (state + 17) & 0xffff; break;
        case 1: state = state ^ 0xa55a; break;
        case 2: state = (state * 3) & 0xffff; break;
        case 3: state = state >> 1; break;
        case 4: state = (state + i * 257) & 0xffff; break;
        case 5: state = ((state << 3) | (state >> 13)) & 0xffff; break;
        case 6: state = (state - 19) & 0xffff; break;
        default: state = (state + (state >> 8)) & 0xffff; break;
        }
    }
    return state;
}
