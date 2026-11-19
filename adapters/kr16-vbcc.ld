/* Same entry address and memory layout as the other USIM adapters. */
ENTRY(start)
SECTIONS {
    . = 0x2800;
    .text : { *(.start) *(.text) }
    .rodata : { *(.rodata) }
    .data : { *(.data) }
    .bss (NOLOAD) : { *(.bss) *(COMMON) }
}
