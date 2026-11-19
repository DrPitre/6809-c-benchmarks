/* Binary search: alternating present and absent keys in 64 sorted words. */
unsigned bench_run(seed)
unsigned seed;
{
    unsigned data[64], base, key, sum;
    int i, low, high, mid, found;
    base = seed & 255;
    for (i = 0; i < 64; ++i)
        data[i] = base + i * 257;
    sum = 0;
    for (i = 0; i < 96; ++i) {
        key = base + (((seed & 63) + i * 13) & 63) * 257 + (i & 1);
        low = 0;
        high = 63;
        found = 0;
        while (low <= high) {
            mid = (low + high) / 2;
            if (data[mid] == key) {
                found = mid + 1;
                break;
            }
            if (data[mid] < key)
                low = mid + 1;
            else
                high = mid - 1;
        }
        sum = (sum * 3 + found) & 0xffff;
    }
    return sum;
}
