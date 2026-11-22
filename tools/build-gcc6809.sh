#!/bin/sh
# Ubuntu: build-essential bison flex curl libgmp-dev libmpfr-dev libmpc-dev texinfo
# Keep the author's compiler source trees in ~/Projects/gcc6809 by default.
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
source_root=${GCC6809_SOURCE_DIR:-"$HOME/Projects/gcc6809/sources"}
prefix=${GCC6809_PREFIX:-"$root/build/gcc6809"}
jobs=${JOBS:-2}
mkdir -p "$root/build/downloads" "$root/build/gcc6809-build" "$source_root" "$prefix"
source_root=$(CDPATH= cd -- "$source_root" && pwd)
prefix=$(CDPATH= cd -- "$prefix" && pwd)
export PATH="$prefix/bin:$PATH"

# FTP filenames include the OpenVMS version number. curl's default TYPE I
# transfers archives in binary mode. Never trust a partial download.
python3 "$root/tools/gcc6809_sources.py" "$source_root"

build="$root/build/gcc6809-build"
target=m6809-unknown-elf
mkdir -p "$build/binutils" "$build/gcc" "$build/newlib"
cd "$build/binutils"
if [ ! -f Makefile ]; then
    "$source_root/binutils-gdb/configure" --target="$target" --prefix="$prefix" \
        --disable-gdb --disable-sim --disable-gprofng --disable-nls --disable-werror
fi
make -j"$jobs" MAKEINFO=true all-binutils all-gas all-ld
make MAKEINFO=true install-binutils install-gas install-ld

cd "$build/gcc"
if [ ! -f Makefile ]; then
    set --
    if [ -n "${GCC6809_HOST_PREFIX:-}" ]; then
        set -- "--with-gmp=$GCC6809_HOST_PREFIX" "--with-mpfr=$GCC6809_HOST_PREFIX" "--with-mpc=$GCC6809_HOST_PREFIX"
    fi
    "$source_root/gcc-16.2.0/configure" --target="$target" --prefix="$prefix" \
        --enable-languages=c --disable-bootstrap --disable-multilib \
        --with-newlib --disable-nls --disable-werror --disable-libssp --disable-libquadmath \
        --disable-libgomp --disable-libsanitizer "$@"
fi
make -j"$jobs" MAKEINFO=true all-gcc
make MAKEINFO=true install-gcc

cd "$build/newlib"
if [ ! -f Makefile ]; then
    "$source_root/newlib-4.6.0/configure" --target="$target" --prefix="$prefix" \
        --disable-multilib CC_FOR_TARGET="$target-gcc" \
        AR_FOR_TARGET="$target-ar" RANLIB_FOR_TARGET="$target-ranlib" \
        CFLAGS_FOR_TARGET='-O2 -m6809'
fi
make -j"$jobs" MAKEINFO=true
make MAKEINFO=true install

cd "$build/gcc"
make -j"$jobs" MAKEINFO=true all-target-libgcc
make MAKEINFO=true install-target-libgcc
cp "$root/tools/gcc6809-sources.json" "$prefix/source-manifest.json"
"$target-gcc" --version
