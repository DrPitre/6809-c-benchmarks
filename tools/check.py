"""Independent reference calculations; host checks are not 6809 measurements."""
from pathlib import Path
import subprocess
import argparse
import json
import os

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (0, 1, 0x1234, 0xffff)


def crc16(seed):
    crc = seed
    for byte in range(256):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ (0x1021 if crc & 0x8000 else 0)) & 0xffff
    return crc


def insertion_sort(seed):
    data = []
    for _ in range(64):
        seed = (seed * 109 + 89) % 65536
        data.append(seed >> 8)
    checksum = 0
    for value in sorted(data):
        checksum = (checksum * 3 + value) % 65536
    return checksum


def mix16(seed):
    for _ in range(1024):
        seed ^= (seed << 7) & 0xffff
        seed ^= seed >> 9
        seed = (seed + 0x9e37) & 0xffff
    return seed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    rows = []
    for reference in (crc16, insertion_sort, mix16):
        expected = [(seed, reference(seed)) for seed in SEEDS]
        try:
            output = subprocess.check_output(
                [str(ROOT / "build" / "host" / reference.__name__)], text=True)
            actual = [tuple(map(int, line.split())) for line in output.splitlines()]
            passed = actual == expected
            detail = output
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            passed, detail = False, str(error)
        rows.append({"benchmark": reference.__name__,
                     "status": "PASS" if passed else "FAIL", "output": detail})
        print(f"{rows[-1]['status']} {reference.__name__}: {len(SEEDS)} seeds")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({
            "compiler": os.environ.get("BENCH_CC", "unknown"),
            "flags": os.environ.get("BENCH_FLAGS", "unknown"),
            "revision": os.environ.get("GITHUB_SHA", "local"),
            "rows": rows}, indent=2) + "\n")
    return 0 if all(row["status"] == "PASS" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
