/* Minimal reproducer for the pinned vbcc 6809 Release 1 Preview (2026-01-25).
 *
 * vbcchc12 -cpu=6809 -pcrel -drel -O=0 vbcc-ed-offset.c -o=offset.s
 * The same issue occurs with -O=1023.
 *
 * The argument must point one past the 256-byte array. The unpatched preview emits
 * LEAX ,S instead, passing the start of the array. ed's subst.c uses this
 * expression for its output-buffer limit, so substitution returns an error.
 */
extern int sink(char *);

int probe(void)
{
    char buf[256];
    return sink(buf + 256);
}
