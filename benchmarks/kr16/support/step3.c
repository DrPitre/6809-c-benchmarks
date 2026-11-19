unsigned step3(a, b, c)
unsigned a, b, c;
{
    return (((a + b) & 0xffff) ^ ((c << 1) & 0xffff) ^ (c >> 7)) & 0xffff;
}
