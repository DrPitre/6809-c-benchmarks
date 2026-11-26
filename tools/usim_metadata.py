"""Identify the pinned CPU core and the benchmark machine used for results."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def emulator_metadata(banner):
    revision = (ROOT / 'tools/usim-revision.txt').read_text().strip()
    expected = 'markrvmurray/usim ' + revision + ' (benchmark adapter)'
    if banner.strip() != expected:
        raise ValueError('USIM executable does not match the pinned core/adapter')
    return {'emulator': expected, 'emulator_revision': revision,
            'emulator_source_url': 'https://github.com/markrvmurray/usim/tree/' + revision,
            'emulator_adapter_sha256': hashlib.sha256(
                (ROOT / 'adapters/usim-bench.cpp').read_bytes()).hexdigest()}
