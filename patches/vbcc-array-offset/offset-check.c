/* SPDX-License-Identifier: BSD-2-Clause */
int check_offset(const char *base, const char *end, unsigned expected)
{
    return (unsigned)(end - base) != expected;
}
