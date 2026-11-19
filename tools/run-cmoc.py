"""Build unchanged kernels for CMOC's USIM target and collect real results."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from check import SEEDS, crc16, insertion_sort, mix16

ROOT = Path(__file__).resolve().parents[1]


def loaded_bytes(path):
    """Count unique loaded data bytes, excluding S-record text and headers."""
    memory = {}
    for line in path.read_text().splitlines():
        if line[:2] not in ("S1", "S2", "S3"):
            continue
        record = bytes.fromhex(line[2:])
        if record[0] != len(record) - 1 or sum(record) & 255 != 255:
            raise ValueError("Invalid S-record")
        width = {"S1": 2, "S2": 3, "S3": 4}[line[:2]]
        address = int.from_bytes(record[1:1 + width], "big")
        for offset, value in enumerate(record[1 + width:-1]):
            if address + offset in memory:
                raise ValueError("Overlapping S-record data")
            memory[address + offset] = value
    if not memory:
        raise ValueError("No S-record data")
    return len(memory)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--optimization", choices=("0", "2"), default="2")
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()
    cmoc = os.environ.get("CMOC", "cmoc")
    usim = os.environ.get("USIM", "usim")
    flags = ["--usim", "-O" + args.optimization, "-I" + str(ROOT / "include")]
    directory = ROOT / "build" / ("cmoc-O" + args.optimization)
    directory.mkdir(parents=True, exist_ok=True)
    commands = []

    def run(command):
        commands.append(command)
        result = subprocess.run(command, cwd=directory, capture_output=True,
                                text=True, timeout=60)
        with (directory / "commands.log").open("a") as log:
            log.write(json.dumps(command) + "\n" + result.stdout + result.stderr)
        result.check_returncode()
        return result.stdout

    (directory / "commands.log").write_text("")
    report = {"compiler": "CMOC", "target": "6809 / USIM", "flags": " ".join(flags[:2]),
              "revision": os.environ.get("GITHUB_SHA", "local"), "rows": [],
              "cycles": None, "emulator": "USIM bundled with CMOC 0.1.99"}
    try:
        report["version"] = run([cmoc, "--version"]).strip()
        report["assembler_version"] = run(["lwasm", "--version"]).strip()
        report["linker_version"] = run(["lwlink", "--version"]).strip()
        run([cmoc, *flags, "-c", "-o", "runner.o", str(ROOT / "adapters/cmoc-usim.c")])
        for reference in (crc16, insertion_sort, mix16):
            name = reference.__name__
            row = {"benchmark": name, "status": "FAIL"}
            try:
                run([cmoc, *flags, "-i", "-c", "-o", name + ".o", str(ROOT / "benchmarks" / (name + ".c"))])
                run([cmoc, *flags, "-i", "-o", name + ".srec", name + ".o", "runner.o"])
                row["assembly"] = {name + ".s": (directory / (name + ".s")).read_text()}
                row["linker_map"] = (directory / (name + ".map")).read_text()
                output = run([usim, name + ".srec"])
                actual = [tuple(map(int, line.split())) for line in output.splitlines()]
                expected = [(seed, reference(seed)) for seed in SEEDS]
                row.update(status="PASS" if actual == expected else "FAIL", output=output,
                           expected=expected, loaded_bytes=loaded_bytes(directory / (name + ".srec")))
                sections = re.findall(r"^Section: code \(" + re.escape(name) + r"\.o\) load at [0-9A-Fa-f]+, length ([0-9A-Fa-f]+)$",
                                      (directory / (name + ".map")).read_text(), re.M)
                if len(sections) != 1:
                    raise ValueError("Expected exactly one kernel code section")
                row["kernel_code_bytes"] = int(sections[0], 16)
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                row.update(status="FAIL", error=str(error))
            report["rows"].append(row)
            print(name, row["status"])
    except (OSError, subprocess.SubprocessError) as error:
        report["error"] = str(error)
    report["commands"] = commands
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2) + "\n")
    return 0 if len(report["rows"]) == 3 and all(r["status"] == "PASS" for r in report["rows"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
