#!/bin/sh
# Release candidate verified on 2026-11-22; deliberately pinned for CI.
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
case "$(uname -s)-$(uname -m)" in
    Darwin-arm64)
        platform=darwin-arm64
        digest=b3997071907c213c7d23e57a7086cd6ec95ea80348d93756d8f0591a8e176ac0 ;;
    Linux-x86_64)
        platform=linux-x86_64
        digest=d3c77f1879da9424a6ed932ef3a63d52a421d42d24884e254be7a3743b9e3072 ;;
    *) echo "Supported release hosts: macOS arm64 and Linux x86_64" >&2; exit 1 ;;
esac
archive="mc6809-toolchain-1.1.0-rc1-$platform.tar.xz"
mkdir -p "$root/build/downloads/llvm"
cd "$root/build/downloads/llvm"
if [ ! -f "$archive" ]; then
    curl --fail --location --retry 3 "https://github.com/markrvmurray/llvm-mc6809/releases/download/RELEASE_1.1.0_rc1/$archive" -o "$archive"
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
