#!/bin/sh
# Ubuntu dependencies: build-essential bison flex curl python3
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
prefix="$root/build/toolchain"
mkdir -p "$root/build/downloads" "$root/build/sources" "$prefix"
cd "$root/build/downloads"
fetch() {
    file=$1
    url=$2
    digest=$3
    if [ ! -f "$file" ]; then curl --fail --location --retry 3 "$url" -o "$file"; fi
    python3 - "$file" "$digest" <<'PY'
import hashlib, pathlib, sys
if hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest() != sys.argv[2]:
    raise SystemExit('Source checksum mismatch: ' + sys.argv[1])
PY
}
fetch cmoc-0.1.99.tar.gz http://gvlsywt.cluster051.hosting.ovh.net/dev/cmoc-0.1.99.tar.gz fd51ba7239a24fe199927bb847ce8bce45bacd238d4984985cd33dfe03c468eb
fetch lwtools-4.24.tar.gz https://www.lwtools.ca/releases/lwtools/lwtools-4.24.tar.gz b38a2baad15c017bb7cd8144218e7af61abccf21fd25f7b1a35e6529acd7b3dd
cd "$root/build/sources"
tar -xzf ../downloads/lwtools-4.24.tar.gz
tar -xzf ../downloads/cmoc-0.1.99.tar.gz
make -C lwtools-4.24 -j2
make -C lwtools-4.24 install PREFIX="$prefix"
export PATH="$prefix/bin:$PATH"
cd cmoc-0.1.99
./configure --prefix="$prefix"
make -j2
make install
cp src/usim-0.91-cmoc/usim "$prefix/bin/usim"
