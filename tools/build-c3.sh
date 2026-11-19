#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
source="$root/build/sources/nitros9-languages"
revision=$(cat "$root/tools/c3-revision.txt")
if [ ! -d "$source/.git" ]; then
    mkdir -p "$source"
    git -C "$source" init
    git -C "$source" remote add origin https://github.com/nitros9project/nitros9-languages.git
    git -C "$source" fetch --depth 1 origin "$revision"
    git -C "$source" checkout --detach FETCH_HEAD
fi
[ "$(git -C "$source" rev-parse HEAD)" = "$revision" ] || {
    echo "C3 source revision mismatch" >&2; exit 1;
}
export PATH="$root/build/toolchain/bin:$PATH"
# Build each required stage explicitly: the upstream aggregate recipe may
# conceal a failing intermediate make behind a later successful stage.
for stage in exec prep comp optx; do
    make -C "$source/c3/build/unix/$stage"
done
cd "$source/c3/lwbackend"
sh buildrt.sh
sh buildlibc.sh
