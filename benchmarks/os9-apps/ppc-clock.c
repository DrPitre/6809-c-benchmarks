/* Fixed clock input for reproducible ppc page headers on every compiler.
 * This replaces only getime; pagination and header formatting remain upstream.
 */
int bench_getime(buffer)
char *buffer;
{
    buffer[0] = 126;
    buffer[1] = 11;
    buffer[2] = 26;
    buffer[3] = 13;
    buffer[4] = 45;
    buffer[5] = 6;
    return 0;
}
