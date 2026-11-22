import hashlib
import io
from pathlib import Path
import sys
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from gcc6809_sources import download_archive, prepare_archive


class GCC6809SourceTests(unittest.TestCase):
    def test_https_mirror_is_verified_before_caching(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'source.tar.bz2'
            payload = b'verified upstream archive bytes'
            item = dict(file=archive.name, sha256=hashlib.sha256(payload).hexdigest(),
                        url='ftp://upstream/source', mirror_url='https://mirror/source')
            def fetch(command, **kwargs):
                self.assertIn(item['mirror_url'], command)
                Path(command[-1]).write_bytes(payload)
            with patch('gcc6809_sources.subprocess.run', side_effect=fetch) as transfer:
                download_archive(item, archive)
            self.assertEqual(transfer.call_count, 1)
            self.assertEqual(archive.read_bytes(), payload)

    def test_unreachable_mirror_falls_back_to_verified_upstream(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'source.tar.bz2'
            payload = b'verified upstream archive bytes'
            item = dict(file=archive.name, sha256=hashlib.sha256(payload).hexdigest(),
                        url='ftp://upstream/source', mirror_url='https://mirror/source')
            def fetch(command, **kwargs):
                if item['mirror_url'] in command:
                    raise subprocess.CalledProcessError(28, command)
                self.assertIn(item['url'], command)
                Path(command[-1]).write_bytes(payload)
            with patch('gcc6809_sources.subprocess.run', side_effect=fetch) as transfer:
                download_archive(item, archive)
            self.assertEqual(transfer.call_count, 2)
            self.assertEqual(archive.read_bytes(), payload)

    def test_corrupt_downloads_never_enter_the_archive_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'source.tar.bz2'
            item = dict(file=archive.name, sha256='expected', url='ftp://upstream/source',
                        mirror_url='https://mirror/source')
            def fetch(command, **kwargs):
                Path(command[-1]).write_bytes(b'damaged download')
            with patch('gcc6809_sources.subprocess.run', side_effect=fetch):
                with self.assertRaisesRegex(SystemExit, 'Source checksum mismatch'):
                    download_archive(item, archive)
            self.assertFalse(archive.exists())

    def archive(self, root):
        archive = root / 'source.tar.bz2'
        files = {'source/hello.c': 'int hello;\n',
                 'source/bfd/config.status': 'config_files=" Makefile po/Makefile.in linked.c"\nconfig_headers=" config.h"\n',
                 'source/bfd/bfdver.h': 'old generated version header',
                 'source/gas/doc/.dirstamp': 'old generated directory stamp',
                 'source/ld/ldscripts/stamp': 'old script directory stamp',
                 'source/ld/em6809elf.c': 'old embedded script',
                 'source/ld/.deps/em6809elf.Pc': 'old absolute source paths',
                 'source/ld/emultempl/elf.em': 'real template',
                 'source/bfd/config.h': '#define HOST_LINUX 1\n',
                 'source/bfd/Makefile': 'stale host paths\n',
                 'source/bfd/po/Makefile.in': 'stale configured output\n',
                 'source/bfd/po/Makefile.in.in': 'real source template\n',
                 'source/bfd/hello.o': 'old object',
                 'source/bfd/libbfd.a': 'old static library',
                 'source/bfd/.libs/libbfd.a': 'old library'}
        with tarfile.open(archive, 'w:bz2') as stream:
            for name, content in files.items():
                item = tarfile.TarInfo(name)
                data = content.encode()
                item.size = len(data)
                stream.addfile(item, io.BytesIO(data))
            link = tarfile.TarInfo('source/bfd/linked.c')
            link.type = tarfile.SYMTYPE
            link.linkname = '../hello.c'
            stream.addfile(link)
        return {'file': archive.name, 'directory': 'source',
                'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}

    def test_verified_sources_lose_archived_host_outputs_and_can_be_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / 'sources'
            destination.mkdir()
            item = self.archive(root)
            prepare_archive(item, root, destination)
            tree = destination / 'source'
            self.assertTrue((tree / 'hello.c').exists())
            self.assertTrue((tree / 'bfd/po/Makefile.in.in').exists())
            self.assertTrue((tree / 'ld/emultempl/elf.em').exists())
            for path in ('bfd/config.status', 'bfd/config.h', 'bfd/Makefile', 'bfd/bfdver.h', 'bfd/linked.c',
                         'bfd/po/Makefile.in', 'bfd/hello.o', 'bfd/libbfd.a', 'bfd/.libs/libbfd.a',
                         'gas/doc/.dirstamp', 'ld/ldscripts/stamp', 'ld/em6809elf.c',
                         'ld/.deps/em6809elf.Pc'):
                self.assertFalse((tree / path).exists(), path)
            prepare_archive(item, root, destination)

    def test_bad_checksum_and_unmanaged_source_tree_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / 'sources'
            destination.mkdir()
            item = self.archive(root)
            with self.assertRaisesRegex(SystemExit, 'Source checksum mismatch'):
                prepare_archive(dict(item, sha256='bad'), root, destination)
            self.assertFalse((destination / 'source').exists())
            tree = destination / 'source'
            tree.mkdir()
            (tree / 'my-work.c').write_text('keep this')
            with self.assertRaisesRegex(SystemExit, 'Existing source tree'):
                prepare_archive(item, root, destination)
            self.assertEqual((tree / 'my-work.c').read_text(), 'keep this')
