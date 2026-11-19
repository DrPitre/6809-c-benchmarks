/* K&R variant: 64 unsigned words holding values 0..255.
 * Arithmetic explicitly wraps at 16 bits on targets and the host. */
unsigned bench_run(seed)
unsigned seed;
{
    unsigned data[64], value;
    unsigned state, checksum;
    int i, j;
    state = seed;
    for (i = 0; i < 64; ++i) {
        state = (state * 109 + 89) & 0xffff;
        data[i] = state >> 8;
    }
    for (i = 1; i < 64; ++i) {
        value = data[i];
        j = i;
        while (j > 0 && data[j - 1] > value) {
            data[j] = data[j - 1];
            --j;
        }
        data[j] = value;
    }
    checksum = 0;
    for (i = 0; i < 64; ++i)
        checksum = (checksum * 3 + data[i]) & 0xffff;
    return checksum;
}
