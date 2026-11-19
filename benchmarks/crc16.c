#include "bench.h"
/* CRC-16/CCITT polynomial, processing bytes 0..255; seed is initial CRC. */
unsigned short bench_run(unsigned short seed)
{
    unsigned short crc;
    unsigned int byte, bit;
    crc = seed;
    for (byte = 0; byte < 256; ++byte) {
        crc = (unsigned short)(crc ^ (unsigned short)(byte << 8));
        for (bit = 0; bit < 8; ++bit) {
            if (crc & 0x8000U)
                crc = (unsigned short)((crc << 1) ^ 0x1021U);
            else
                crc = (unsigned short)(crc << 1);
        }
    }
    return crc;
}
