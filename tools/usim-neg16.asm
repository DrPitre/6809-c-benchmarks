* Check all 65536 inputs to vbcc's valid 16-bit negation sequence.
        org $2800
start   lds #$fe00
        ldx #0
loop    tfr x,d
        nega
        negb
        sbca #0
        std $1000
* Independent reference: complement both bytes, then add one as a word.
        tfr x,d
        coma
        comb
        addd #1
        cmpd $1000
        bne fail
        leax 1,x
        bne loop
        ldd #0
        sync
fail    ldd #1
        sync
        end start
