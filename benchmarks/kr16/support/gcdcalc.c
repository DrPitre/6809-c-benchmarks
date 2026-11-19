unsigned gcdcalc(a, b)
unsigned a, b;
{
    if (b == 0)
        return a;
    return gcdcalc(b, a % b);
}
