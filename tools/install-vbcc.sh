#!/bin/sh
# Author's 6809 Release 1 Preview, dated 2026-01-25.
set -eu
cd "$(dirname "$0")/.."
mkdir -p build/downloads build/sources build/vbcc
archive=build/downloads/vbcc6809_20260125.zip
if [ ! -f "$archive" ]; then
    curl -fL --retry 3 --retry-all-errors http://www.compilers.de/vbcc6809_20260125.zip -o "$archive"
fi
python3 - "$archive" <<'PY'
import hashlib, pathlib, sys, zipfile
archive = pathlib.Path(sys.argv[1])
expected = '18db043d4d4c8b0a16d4fa4b813616f277fcfb3667be0eda2334a8b8b024917e'
if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
    raise SystemExit('vbcc archive checksum mismatch')
with zipfile.ZipFile(archive) as z:
    z.extractall('build/sources')
PY
case "$(uname -s)-$(uname -m)" in
    Linux-x86_64)
        cp -R build/sources/vbcc6809/vbcc6809_linux/vbcc/. build/vbcc/
        chmod +x build/vbcc/bin/*
        ;;
    *)
        echo 'This installer uses the pinned Linux x86_64 binaries. See README for native build notes.' >&2
        exit 1
        ;;
esac
