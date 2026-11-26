#!/bin/sh
# Build only the pinned 6809 CPU and the benchmark machine; no SDL/firmware.
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
source="$root/build/sources/markrvmurray-usim"
revision=$(cat "$root/tools/usim-revision.txt")
mkdir -p "$root/build/toolchain/bin"
if [ ! -d "$source/.git" ]; then
    mkdir -p "$source"
    git -C "$source" init
    git -C "$source" remote add origin https://github.com/markrvmurray/usim.git
    git -C "$source" fetch --depth 1 origin "$revision"
    git -C "$source" checkout --detach FETCH_HEAD
fi
[ "$(git -C "$source" rev-parse HEAD)" = "$revision" ] || {
    echo 'USIM source revision mismatch' >&2; exit 1;
}
[ -z "$(git -C "$source" status --porcelain --untracked-files=no)" ] || {
    echo 'USIM source has local modifications' >&2; exit 1;
}
"${CXX:-c++}" -std=c++20 -O2 -g -Wall -Wextra -Werror -I"$source" \
    -DUSIM_REVISION=\""$revision"\" \
    "$root/adapters/usim-bench.cpp" "$source/usim.cpp" "$source/memory.cpp" \
    "$source/mc6809.cpp" "$source/mc6809in.cpp" \
    -o "$root/build/toolchain/bin/usim"
python3 "$root/tools/check-usim-machine.py"
python3 "$root/tools/check-usim-count.py"
python3 "$root/tools/check-usim-neg.py" --lwasm "$root/build/toolchain/bin/lwasm" --usim "$root/build/toolchain/bin/usim"
