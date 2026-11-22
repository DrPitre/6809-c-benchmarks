/* Plain 6809 ELF, loaded by the common bare-metal USIM harness. */
ENTRY(start)
SECTIONS
{
    . = 0x2800;
    .start : { KEEP(harness.o(.start)) }
    .text : { *(.text .text.*) }
    .rodata : { *(.rodata .rodata.*) }
    .data : { *(.data .data.*) }
    .bss (NOLOAD) : { *(.bss .bss.*) *(COMMON) }
    ASSERT(SIZEOF(.bss) == 0, "The kr16 harness does not initialize BSS")
    ASSERT(. <= 0xee00, "Program overlaps reserved 4 KiB stack")
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
