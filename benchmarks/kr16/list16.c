/* Structure fields and a pointer-linked permutation of 32 stack nodes. */
struct node {
    unsigned value;
    struct node *next;
};
unsigned bench_run(seed)
unsigned seed;
{
    struct node nodes[32], *p;
    unsigned i, sum;
    for (i = 0; i < 32; ++i) {
        nodes[i].value = (seed + i * 4051) & 0xffff;
        nodes[i].next = &nodes[(i + 17) & 31];
    }
    p = &nodes[seed & 31];
    sum = 0;
    for (i = 0; i < 64; ++i) {
        sum = ((sum * 3) ^ p->value) & 0xffff;
        p = p->next;
    }
    return sum;
}
