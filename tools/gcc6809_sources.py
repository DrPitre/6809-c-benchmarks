"""Verify the dated upstream archives and prepare clean compiler source trees."""
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys


def archive_digest(archive):
    checksum = hashlib.sha256()
    with archive.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def download_archive(item, archive):
    partial = archive.with_suffix(archive.suffix + '.part')
    failures = []
    for url in filter(None, (item.get('mirror_url'), item['url'])):
        try:
            print('Downloading ' + item['file'] + ' from ' + url, flush=True)
            subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                            '--connect-timeout', '20', '--max-time', '3600',
                            '--retry', '2', '--retry-connrefused',
                            url, '-o', str(partial)], check=True)
            if archive_digest(partial) != item['sha256']:
                raise ValueError('Source checksum mismatch: ' + url)
            partial.replace(archive)
            return
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            failures.append(str(error))
    raise SystemExit('Unable to download verified source ' + item['file'] + ':\n' + '\n'.join(failures))


def prepare_archive(item, downloads, destination):
    archive = downloads / item['file']
    if not archive.exists():
        download_archive(item, archive)
    digest = archive_digest(archive)
    if digest != item['sha256']:
        raise SystemExit('Source checksum mismatch: ' + str(archive))
    tree = destination / item['directory']
    marker = tree / '.benchmark-archive-sha256'
    if tree.exists():
        if not marker.exists() or marker.read_text().strip() != digest:
            raise SystemExit('Existing source tree is not from this pinned installer: ' + str(tree) +
                             '\nChoose an empty GCC6809_SOURCE_DIR; existing sources are preserved.')
    else:
        # Upstream archives include Linux build outputs; exclude those so that
        # configuration and all target objects come from this host's build.
        subprocess.run(['tar', '-xjf', str(archive), '-C', str(destination),
                        '--exclude=*/build', '--exclude=*/.git', '--exclude=*/.deps',
                        '--exclude=*.o', '--exclude=*.lo', '--exclude=*/.libs',
                        '--exclude=*.a', '--exclude=*.la', '--exclude=*.lai',
                        '--exclude=*/autom4te.cache'], check=True)
        # These archives contain in-source Linux configure results as well as
        # objects. Remove generated outputs named by each config.status before
        # an out-of-tree build; do not run stale host-specific Makefiles.
        for status in tree.rglob('config.status'):
            generated = ['Makefile', 'config.h', 'config.cache', 'config.log',
                         'libtool', 'stamp-h1', 'config.status']
            for names in re.findall(r'^(?:config_files|config_headers)="([^"]*)"',
                                    status.read_text(errors='replace'), re.M):
                generated.extend(name.split(':')[0] for name in shlex.split(names))
            for name in generated:
                output = status.parent / name
                if tree.resolve() not in output.resolve().parents:
                    raise SystemExit('Invalid generated source path: ' + str(output))
                if output.is_file() or output.is_symlink():
                    output.unlink()
        marker.write_text(digest + '\n')
    # Automake uses these to create build directories. Archived source-tree
    # stamps can otherwise satisfy VPATH without creating the new directories.
    for stamp in tree.rglob('.dirstamp'):
        stamp.unlink()
    for cache in list(tree.rglob('.deps')):
        if cache.is_symlink():
            cache.unlink()
        elif cache.is_dir():
            shutil.rmtree(cache)
    # BFD's version-header recipe also creates libtool-soversion. A shipped
    # bfdver.h can satisfy VPATH while leaving that side output missing in a
    # fresh build. These are generated files listed in BFD/GAS Makefile.in.
    for relative in ('bfd/bfd.h', 'bfd/bfdver.h', 'bfd/elf32-target.h',
                     'bfd/elf64-target.h', 'bfd/targmatch.h', 'bfd/ofiles',
                     'bfd/stamp-ofiles', 'bfd/libtool-soversion',
                     'gas/targ-cpu.h', 'gas/obj-format.h', 'gas/targ-env.h',
                     'gas/itbl-cpu.h', 'gas/cgen-desc.h'):
        output = tree / relative
        if output.is_file() or output.is_symlink():
            output.unlink()
    # ld/Makefile.in calls these STAGESTUFF. Regenerate scripts and their
    # embedded C versions for this install prefix, rather than using VPATH
    # copies from the author's in-source build.
    scripts = tree / 'ld/ldscripts'
    if scripts.is_symlink():
        scripts.unlink()
    elif scripts.is_dir():
        shutil.rmtree(scripts)
    for output in (tree / 'ld').glob('e*.c'):
        output.unlink()
    emulations = tree / 'ld/ldemul-list.h'
    if emulations.exists():
        emulations.unlink()


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: gcc6809_sources.py SOURCE_DIRECTORY')
    root = Path(__file__).resolve().parents[1]
    destination = Path(sys.argv[1]).resolve()
    downloads = root / 'build/downloads'
    downloads.mkdir(parents=True, exist_ok=True)
    destination.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root / 'tools/gcc6809-sources.json').read_text())
    for item in manifest['archives']:
        prepare_archive(item, downloads, destination)


if __name__ == '__main__':
    main()

