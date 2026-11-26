#!/bin/sh
# Ubuntu dependencies: build-essential bison flex curl python3
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
prefix="$root/build/toolchain"
cmoc_version=${CMOC_VERSION:-0.1.101}
case "$cmoc_version" in
    0.1.99|0.1.101) ;;
    *) echo "Unsupported pinned CMOC version: $cmoc_version" >&2; exit 1 ;;
esac
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
if [ "$cmoc_version" = 0.1.101 ]; then
    fetch cmoc-0.1.101.tar.gz http://gvlsywt.cluster051.hosting.ovh.net/dev/cmoc-0.1.101.tar.gz cfd8cead5c57c4bada35a9f1e74fe914a0f41633dec7fcc6ca7dcc54adc43fd3
fi
fetch lwtools-4.24.tar.gz https://www.lwtools.ca/releases/lwtools/lwtools-4.24.tar.gz b38a2baad15c017bb7cd8144218e7af61abccf21fd25f7b1a35e6529acd7b3dd
cd "$root/build/sources"
tar -xzf ../downloads/lwtools-4.24.tar.gz
tar -xzf ../downloads/cmoc-0.1.99.tar.gz
if [ "$cmoc_version" != 0.1.99 ]; then tar -xzf "../downloads/cmoc-$cmoc_version.tar.gz"; fi
make -C lwtools-4.24 -j2
make -C lwtools-4.24 install PREFIX="$prefix"
export PATH="$prefix/bin:$PATH"
patch -d cmoc-0.1.99 -p1 < "$root/fixes/usim-neg-carry/usim-neg-carry.patch"
python3 "$root/tools/instrument-usim.py" cmoc-0.1.99/src/usim-0.91-cmoc
cd "cmoc-$cmoc_version"
./configure --prefix="$prefix"
make -j2
make install
# Keep the simulator fixed across compiler releases.
if [ "$cmoc_version" != 0.1.99 ]; then
    cd "$root/build/sources/cmoc-0.1.99"
    ./configure --prefix="$prefix"
    make -C src/usim-0.91-cmoc -j2
fi
cp src/usim-0.91-cmoc/usim "$prefix/bin/usim"
python3 "$root/tools/check-usim-count.py"

python3 "$root/fixes/usim-neg-carry/check-neg.py" --lwasm "$prefix/bin/lwasm" --usim "$prefix/bin/usim"
