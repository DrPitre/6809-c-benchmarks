/* CRC-16/CCITT polynomial, processing bytes 0..255; seed is initial CRC. */
unsigned bench_run(seed)
unsigned seed;
{
    unsigned crc;
    unsigned byte, bit;
    crc = seed;
    for (byte = 0; byte < 256; ++byte) {
        crc = (unsigned)(crc ^ (unsigned)(byte << 8));
        for (bit = 0; bit < 8; ++bit) {
            if (crc & 0x8000)
                crc = (((crc << 1) ^ 0x1021) & 0xffff);
            else
                crc = ((crc << 1) & 0xffff);
        }
    }
    return crc;
}
