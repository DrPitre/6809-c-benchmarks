/* Redirected terminal adapter: retain the ANSI display and editor loop.
 * Read raw OS-9 bytes so control keys reach the editor unchanged.
 * Exhausted scripts fail immediately instead of looping on stale input.
 */
#include <stdio.h>
#include <stdlib.h>
int read();
int write();
int ttopen() { return 0; }
int ttclose() { return 0; }
int ttflush() { return fflush(stdout); }
int ttputc(c)
int c;
{
    char byte;
    byte = c;
    return write(1, &byte, 1) == 1 ? 0 : -1;
}
int ttgetc()
{
    char byte;
    if (read(0, &byte, 1) != 1) {
        write(2, "UEMACS SCRIPT EXHAUSTED\r", 24);
        exit(1);
    }
    return byte & 255;
}
