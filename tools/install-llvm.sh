#!/bin/sh
# Latest stable release verified on 2026-11-19; deliberately pinned for CI.
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
case "$(uname -s)-$(uname -m)" in
    Darwin-arm64)
        platform=darwin-arm64
        digest=417695f35adff902b6e79333c7169fc6808529cf342261656c08c0ef1478296e ;;
    Linux-x86_64)
        platform=linux-x86_64
        digest=6fb47e6cfe763d0b8cd60683e52293582d6384ca726e949b4fbc4e8c15768a77 ;;
    *) echo "Supported release hosts: macOS arm64 and Linux x86_64" >&2; exit 1 ;;
esac
archive="mc6809-toolchain-1.0-$platform.tar.xz"
mkdir -p "$root/build/downloads/llvm" "$root/build/llvm"
cd "$root/build/downloads/llvm"
if [ ! -f "$archive" ]; then
    curl --fail --location --retry 3 "https://github.com/markrvmurray/llvm-mc6809/releases/download/RELEASE_1.0/$archive" -o "$archive"
fi
python3 - "$archive" "$digest" <<'PY'
import hashlib, pathlib, sys
if hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest() != sys.argv[2]:
    raise SystemExit('LLVM release checksum mismatch')
PY
tar -xf "$archive" -C "$root/build/llvm" --strip-components=1
"$root/build/llvm/bin/mc6809-clang" --version
