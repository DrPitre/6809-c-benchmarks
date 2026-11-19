"""Shared-suite inventory and independent reference calculations."""
import math
from check import crc16, insertion_sort, mix16


def mul16(seed):
    return sum(((seed + (i + 1) * 4051) % 65536) *
               ((257 + (i + 1) * 257) % 65536) for i in range(256)) % 65536


def div16(seed):
    total = 0
    for i in range(192):
        value = (seed + (i + 1) * 4051) % 65536
        divisor = (i * 37 + seed % 256) % 255 + 1
        quotient, remainder = divmod(value, divisor)
        total += quotient + 17 * remainder
    return total % 65536


def copy16(seed):
    values = []
    for _ in range(64):
        seed = (seed * 109 + 89) % 65536
        values.append(seed)
    shifted = values[1:] + values[-1:]
    return sum(value ^ (i * 257) for i, value in enumerate(shifted)) % 65536


def search16(seed):
    checksum = 0
    for i in range(96):
        # Even queries hit at this index; odd queries lie one past a value.
        found = ((seed % 64 + i * 13) % 64 + 1) if i % 2 == 0 else 0
        checksum = (checksum * 3 + found) % 65536
    return checksum


def switch16(seed):
    state = seed
    for i in range(256):
        operations = (lambda x: x + 17, lambda x: x ^ 0xa55a,
                      lambda x: x * 3, lambda x: x // 2,
                      lambda x: x + i * 257,
                      lambda x: (x * 8) | (x // 8192),
                      lambda x: x - 19, lambda x: x + x // 256)
        state = operations[(state ^ i) % 8](state) % 65536
    return state


def calls16(seed):
    state = seed
    for i in range(128):
        c = (seed ^ (i * 257)) % 65536
        state = ((state + i + 1) % 65536) ^ ((c * 2) % 65536) ^ (c // 128)
    return state


def gcd16(seed):
    return sum(math.gcd((seed + i * 257) % 65536, i * 37 + 1)
               for i in range(64)) % 65536


def signed16(seed):
    value = seed % 2048 - 1024
    checksum = 0
    for i in range(128):
        delta = i * 37 % 101 - 50
        value += (97 + delta) if value < 0 else (-89 - delta)
        checksum += value
    return checksum % 65536


def list16(seed):
    checksum = 0
    for i in range(64):
        index = (seed % 32 + i * 17) % 32
        value = (seed + index * 4051) % 65536
        checksum = ((checksum * 3) ^ value) % 65536
    return checksum


REFERENCES = (crc16, insertion_sort, mix16, mul16, div16, copy16,
              search16, switch16, calls16, gcd16, signed16, list16)
BENCHMARKS = tuple(reference.__name__ for reference in REFERENCES)
LABELS = dict(zip(BENCHMARKS, ('CRC16', 'Insertion sort', '16-bit arithmetic',
    'Multiplication', 'Division and remainder', 'Word copy', 'Binary search',
    'Switch dispatch', 'Function calls', 'Recursive GCD', 'Signed arithmetic',
    'Linked structures')))
PURPOSES = dict(zip(BENCHMARKS, (
    'CRC-16/CCITT over 256 byte values.',
    'Sort 64 unsigned words containing byte values.',
    '1,024 rounds of shifts, XOR, and addition.',
    '256 variable unsigned products with 16-bit wraparound.',
    '192 unsigned quotient/remainder calculations with nonzero divisors.',
    'Copy 64 words through pointers, then shift overlapping storage.',
    '96 alternating present/absent queries in a sorted 64-word array.',
    '256 state-dependent choices across eight switch branches.',
    '128 three-argument calls to a separately compiled function.',
    '64 Euclidean GCD calculations using a separately compiled recursive function.',
    '128 signed comparisons and bounded additions/subtractions without overflow.',
    'Traverse a pointer-linked permutation of 32 stack-allocated structures.')))
SUPPORT = {'calls16': ('support/step3.c',), 'gcd16': ('support/gcdcalc.c',)}


def sources(name):
    return (name + '.c',) + SUPPORT.get(name, ())
