#!/bin/sh
# Release candidate published 2026-11-24; SHA-256 pinned for CI.
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
case "$(uname -s)-$(uname -m)" in
    Darwin-arm64)
        platform=darwin-arm64
        digest=32fc2e08555296e1b5779b6c996f0ce2b268ed9e0d6e4cf9d667b4195f1657b3 ;;
    Linux-x86_64)
        platform=linux-x86_64
        digest=719165c7fecc9ac3842a4f1f48f6e306838e35f1daeddab7a51146063bdaa915 ;;
    *) echo "Supported release hosts: macOS arm64 and Linux x86_64" >&2; exit 1 ;;
esac
archive="mc6809-toolchain-1.1.0-rc2-$platform.tar.xz"
mkdir -p "$root/build/downloads/llvm"
cd "$root/build/downloads/llvm"
if [ ! -f "$archive" ]; then
    curl --fail --location --retry 3 "https://github.com/markrvmurray/llvm-mc6809/releases/download/RELEASE_1.1.0_rc2/$archive" -o "$archive"
fi
python3 - "$archive" "$digest" <<'PY'
import hashlib, pathlib, sys
if hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest() != sys.argv[2]:
    raise SystemExit('LLVM release checksum mismatch')
PY
# Install a complete bundle so files from an older release cannot linger.
staging=$(mktemp -d "$root/build/llvm-install.XXXXXX")
tar -xf "$archive" -C "$staging" --strip-components=1
if [ -d "$root/build/llvm" ]; then
    previous=$(mktemp -d "$root/build/llvm-previous.XXXXXX")
    mv "$root/build/llvm" "$previous/toolchain"
fi
mv "$staging" "$root/build/llvm"
"$root/build/llvm/bin/mc6809-clang" --version

# Keep the compiler at RC2; rebuild only its default 6809 OS-9 C library.
python3 "$root/tools/build-llvm-os9-runtime.py"
