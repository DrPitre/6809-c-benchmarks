/* SPDX-License-Identifier: BSD-2-Clause
 * Compile this file separately from offset-check.c; do not enable LTO/WPO.
 * The independent checker must see the actual pointer arguments.
 */
#include <stdio.h>
extern int check_offset(const char *, const char *, unsigned);

#define ARRAY_CASE(N) \
static int case##N(void) { \
    char buf[N]; \
    return check_offset(buf, buf + N, sizeof(buf)); \
}
ARRAY_CASE(1)
ARRAY_CASE(127)
ARRAY_CASE(128)
ARRAY_CASE(254)
ARRAY_CASE(255)
ARRAY_CASE(256)
ARRAY_CASE(257)
ARRAY_CASE(511)

static int short_array(void)
{
    short buf[128];
    return check_offset((char *)buf, (char *)(buf + 128), sizeof(buf));
}
static int static_array(void)
{
    static char buf[256];
    return check_offset(buf, buf + 256, sizeof(buf));
}
static int commuted(void)
{
    char buf[256];
    return check_offset(buf, 256 + buf, sizeof(buf));
}
static int from_end(void)
{
    char buf[256];
    return check_offset(buf, (buf + 256) - 128, 128);
}
int main(void)
{
    int failed = case1() + case127() + case128() + case254() + case255()
               + case256() + case257() + case511() + short_array()
               + static_array() + commuted() + from_end();
    if (failed) {
        printf("ARRAY-OFFSET FAIL %d\n", failed);
        return 1;
    }
    puts("ARRAY-OFFSET PASS");
    return 0;
}
