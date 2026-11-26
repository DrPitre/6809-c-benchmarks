# vbcc one-past array-offset fix

For the 6809 Release 1 Preview dated 2026-01-25 (vbcc V0.9i pre).
The fix is in the common frontend, `type_expr.c:best_addi2pt`, rather than the
6809 backend. It corrects the candidate offset-type boundaries for unsigned
and signed char, short and int.

An array of N bytes permits forming a pointer N bytes past its start. The
old checks admitted N == MAX + 1 when choosing a narrow offset type. For a
256-byte array the chosen unsigned-char offset cannot represent 256, which
becomes zero. Require N <= MAX instead. Smaller representable arrays retain
the optimization.

## Apply

From the root of the extracted `vbcc` source directory:

```sh
patch -p1 < /path/to/fix.patch
make TARGET=hc12
```

Original source archive SHA-256:
`e1e80894c972bc38a1fe2804fe4bce8559e4be6e53e4c878de6f459a6929637e`

Original `type_expr.c` SHA-256:
`3efdd0064263dfdb68a53edf6abf45ed546b272451c3107db2106ab304005b91`

This archive is inside `vbcc6809_20260125.zip`, SHA-256:
`18db043d4d4c8b0a16d4fa4b813616f277fcfb3667be0eda2334a8b8b024917e`.

## Regression

Compile `array-offset.c` and `offset-check.c` separately and link them with
the normal target runtime. Do not enable whole-program optimization or LTO.
For example, with the supplied vc OS-9 configuration:

```sh
vc +os9 -O0 array-offset.c offset-check.c -o array0
vc +os9 -O2 array-offset.c offset-check.c -o array2
```

The benchmark invokes vbcchc12 with `-cpu=6809 -pcrel -drel -O=0` and
`-O=1023`, assembles each translation unit separately with vasm, and links
with vlink's OS-9 target. The source and complete commands are recorded in
the benchmark artifacts.

The independent checker compares actual pointer distances. Twelve cases
cover sizes 1, 127, 128, 254, 255, 256, 257 and 511, plus short arrays, static
storage, commuted addition, and arithmetic back from a one-past pointer.

On a real NitrOS-9 Level 2 kernel in Pico-Thing USIM:

- Original preview: `ARRAY-OFFSET FAIL 4`, exit status 1, at both settings.
- Patched compiler: `ARRAY-OFFSET PASS`, exit status 0, at both settings.
- All 320 application fixtures pass, including ed substitution and saved-file
  read-back at both vbcc settings.

The test cases are C89 and carry a BSD-2-Clause SPDX identifier. The patch
retains the original compiler source's licensing terms. `email.txt` is a
ready-to-send draft; the preview README supplies the author's address.
