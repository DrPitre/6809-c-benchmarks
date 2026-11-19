; Minimal bare-metal harness for kernels with no static storage.
; C3 passes the first unsigned argument in D; CMOC passes it on the stack.
; vbcc also passes its first argument and result in D.
; C3/CMOC return in D; LLVM takes its first argument and returns in X.
; Output is seed/result in hex.
        section start
        export start
        ifdef LLVM_ABI
        import bench_run
        else
        ifdef VBCC_ABI
        import bench_run
        else
        ifdef CMOC_ABI
        import _bench_run
        else
        import bench_ru
        endc
        endc
        endc
        export _stkcheck
        export _rpterr
start
        lds #$fe00
        ldy #0
        clra
        tfr a,dp
        ldd #0
        lbsr sample
        ldd #1
        lbsr sample
        ldd #$1234
        lbsr sample
        ldd #$ffff
        lbsr sample
        ldd #0
        sync
sample
        pshs d
        lbsr hexword
        lda #32
        sta $ff00
        ldd ,s
        ifdef LLVM_ABI
        tfr d,x
        lbsr bench_run
        tfr x,d
        else
        ifdef VBCC_ABI
        lbsr bench_run
        else
        ifdef CMOC_ABI
        lbsr _bench_run
        else
        lbsr bench_ru
        endc
        endc
        endc
        leas 2,s
        lbsr hexword
        lda #10
        sta $ff00
        rts
hexword
        pshs d
        tfr a,b
        lbsr hexbyte
        ldb 1,s
        lbsr hexbyte
        puls d,pc
hexbyte
        pshs b
        lsrb
        lsrb
        lsrb
        lsrb
        lbsr nibble
        puls b
        andb #15
nibble
        cmpb #10
        blo digit
        addb #7
digit
        addb #48
        stb $ff00
        rts
; C3 emits a stack-check call. This fixed-stack harness has no OS-9 runtime;
; the bounded kernels use well under the reserved 4 KiB stack region.
_stkcheck
        rts
; Runtime arithmetic errors (such as division by zero) must fail the run.
_rpterr
        ldd #1
        sync
        endsection
