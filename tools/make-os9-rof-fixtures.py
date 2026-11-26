"""Generate small ROF archives independently of the splitter under test."""
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]


def word(n):
    return struct.pack('>H', n)


def reference(flag, offset):
    return struct.pack('>BH', flag, offset)


def module(name, code=b'', data=b'', direct=b'', globals=(), externals=(), locals=()):
    header = struct.pack('>IBBB5sBB7H', 0x62cd2387, 0x11, 0x80, 0,
                         bytes([26, 11, 26, 13, 10]), 1, 0,
                         0, 0, len(data), len(direct), len(code), 256, 0)
    definitions = word(len(globals))
    for symbol, flag, offset in globals:
        definitions += symbol.encode() + b'\0' + reference(flag, offset)
    refs = word(len(externals))
    for symbol, entries in externals:
        refs += symbol.encode() + b'\0' + word(len(entries))
        refs += b''.join(reference(*r) for r in entries)
    refs += word(len(locals)) + b''.join(reference(*r) for r in locals)
    return header + name.encode() + b'\0' + definitions + code + direct + data + refs


def fixtures():
    groups = [
        ('empty-archive', []),
        ('single-module', [('one', module('one', code=b'\x39'))]),
        ('multiple-modules', [('first', module('first', code=b'\x86\x01\x39')),
                              ('second', module('second', code=b'\x39', data=b'hello\0'))]),
        ('all-byte-values', [('binary', module('binary', code=bytes(range(256)),
                                               direct=b'\0\r\n\x80\xff', data=bytes(reversed(range(256)))))]),
        ('symbols-and-references', [('refs', module('refs', code=bytes(range(32)),
            direct=b'\r\n\0', data=b'\xff\x80\r\n',
            globals=[('entry', 4, 0), ('data', 1, 2)],
            externals=[('outside', [(0x20, 10), (0x20, 13)])],
            locals=[(0x20, 3), (0x20, 10), (0x20, 13)]))]),
    ]
    cases = []
    for id, modules in groups:
        listing = ''.join(name + '\n' + ('        entry\n        data\n' if name == 'refs' else '')
                          for name, _ in modules)
        outputs = {'LIST': {'path': 'modlist', 'text': listing}}
        outputs.update({name: {'path': 'X.' + name + '.r', 'hex': raw.hex()} for name, raw in modules})
        cases.append({'id': id, 'app': 'lb', 'args': ['INPUT'], 'isolated': True,
                      'input_hex': b''.join(raw for _, raw in modules).hex(), 'output': '',
                      'output_files': outputs})
    return cases


if __name__ == '__main__':
    path = ROOT / 'benchmarks/os9-apps/cases.json'
    cases = [c for c in json.loads(path.read_text()) if c['app'] != 'lb'] + fixtures()
    path.write_text(json.dumps(cases, indent=2) + '\n')
