"""Read measurement boundaries and counters without changing target binaries."""
import re


def boundary_address(maptext, symbol):
    patterns = (
        r'^Symbol: ' + re.escape(symbol) + r' \(harness\.o\) = ([0-9A-Fa-f]+)$',
        r'^\s*([0-9A-Fa-f]+)\s+[0-9A-Fa-f]+\s+0\s+1\s+' + re.escape(symbol) + r'$',
        r'^\s*0x([0-9A-Fa-f]+) ' + re.escape(symbol) + r': global reloc, size 0$',
    )
    matches = [m for pattern in patterns for m in re.findall(pattern, maptext, re.M)]
    if len(matches) != 1:
        raise ValueError('Expected one harness measurement boundary: ' + symbol)
    return int(matches[0], 16)


def instruction_counts(stderr, seeds):
    counts = [int(n) for n in re.findall(r'^BENCH_INSTRUCTIONS ([0-9]+)$', stderr, re.M)]
    if len(counts) != len(seeds) or any(n <= 0 for n in counts):
        raise ValueError('Missing or incomplete USIM instruction counts')
    return [{'seed': seed, 'instructions': count} for seed, count in zip(seeds, counts)]


def code_size_without_harness(maptext, loaded_bytes):
    """Count loaded benchmark/helper bytes, excluding the exact harness range."""
    start = boundary_address(maptext, 'start')
    end = boundary_address(maptext, 'harness_end')
    harness_bytes = end - start
    if harness_bytes <= 0 or loaded_bytes <= harness_bytes:
        raise ValueError('Invalid harness or loaded size')
    return loaded_bytes - harness_bytes, harness_bytes
