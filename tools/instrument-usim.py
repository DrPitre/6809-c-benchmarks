"""Add opt-in instruction counting to the pinned CMOC USIM execution loop."""
import sys
from pathlib import Path

path = Path(sys.argv[1]) / 'usim.cc'
source = path.read_text()
marker = '// BENCH instruction counting v1'
if marker not in source:
    before = '\twhile (!halted) {\n\t\texecute();'
    after = '''    // BENCH instruction counting v1
    const char *beginText = getenv("USIM_BENCH_BEGIN");
    const char *endText = getenv("USIM_BENCH_END");
    const bool measuring = beginText && endText;
    const Word beginPC = measuring ? strtoul(beginText, NULL, 16) : 0;
    const Word endPC = measuring ? strtoul(endText, NULL, 16) : 0;
    bool counting = false;
    unsigned long long instructions = 0;
    while (!halted) {
        if (measuring && pc == endPC && counting) {
            fprintf(stderr, "BENCH_INSTRUCTIONS %llu\\n", instructions);
            counting = false;
        }
        if (measuring && pc == beginPC) {
            instructions = 0;
            counting = true;
        }
        if (counting)
            ++instructions;
        execute();
        // Bare-metal benchmark runs must not depend on host wall-clock IRQs.
        if (measuring)
            continue;'''
    if source.count(before) != 1:
        raise SystemExit('Unexpected USIM source; refusing to apply instrumentation')
    path.write_text(source.replace(before, after))
