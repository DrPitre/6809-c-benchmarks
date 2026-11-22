/* Bare-metal ELF layout matching the common USIM harness.
 * Direct-page register addresses follow LLVM-MC6809 picolibc.ld.
 * The kernels have no static variables; the ABI reserves 24 scratch bytes. */
ENTRY(start)
SECTIONS {
  . = 0x2800;
  .text : { *(.start) *(.text .text.*) }
  .rodata : { *(.rodata .rodata.*) }
  .data : { *(.data .data.*) }
  .bss (NOLOAD) : { *(.bss .bss.*) *(COMMON) }
}
__dp_base_addr = 0;
__rc0 = 0;
__rc1 = 1;
__rc2 = 2;
__rc3 = 3;
__rc4 = 4;
__rc5 = 5;
__rc6 = 6;
__rc7 = 7;
__rc8 = 16;
__rc9 = 17;
__rc10 = 18;
__rc11 = 19;
__rc12 = 20;
__rc13 = 21;
__rc14 = 22;
__rc15 = 23;
__rs0 = 8;
__rs0hi = __rs0;
__rs0lo = __rs0 + 1;
__rs1 = 10;
__rs1hi = __rs1;
__rs1lo = __rs1 + 1;
__rs2 = 12;
__rs2hi = __rs2;
__rs2lo = __rs2 + 1;
__rs3 = 14;
__rs3hi = __rs3;
__rs3lo = __rs3 + 1;
