# USIM NEG carry fix

Apply `usim-neg-carry.patch` to CMOC 0.1.99's bundled
`src/usim-0.91-cmoc/mc6809in.cc` before building the benchmark simulator.
`tools/build-cmoc.sh` applies it to freshly extracted, checksum-verified source
for either supported CMOC compiler version. The simulator stays pinned to
0.1.99 independently of the selected compiler release.

The 6809 NEG instruction clears C only for operand zero. USIM copied bit 8
of `(~operand & 255) + 1` directly into C, producing the opposite result.
Invert that bit to obtain the required borrow flag. This affects NEGA, NEGB,
and memory NEG through their shared helper.

The unchanged vbcc sequence `NEGA; NEGB; SBCA #0` then computes correct word
negation. For input `$0001`, the old simulator produced `$00FF`; the corrected
simulator produces `$FFFF`.

The fix and reproducer were sent to CMOC maintainer Pierre Sarrazin. Current
Ray Bellis upstream USIM already handles this correctly. Remove the local
patch when updating the pinned simulator to a release containing the fix.

`check-neg.py` checks result and N/Z/V/C for all 256 inputs to NEGA, NEGB,
and direct/indexed/extended NEG. H is undefined and is not checked.
`neg16.asm` independently checks all 65,536 word inputs to the emitted
negation sequence against complement-plus-one. The build runs both checks
and the existing instruction-counter check.

```sh
python3 fixes/usim-neg-carry/check-neg.py \
  --lwasm "$PWD/build/toolchain/bin/lwasm" \
  --usim "$PWD/build/toolchain/bin/usim"
```
