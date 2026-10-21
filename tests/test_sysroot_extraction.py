import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('sysroot_stage', Path(__file__).resolve().parents[1] / 'scripts/stage-chromium71-sysroot.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class SysrootExtraction(unittest.TestCase):
    def test_root_entry_and_internal_dangling_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'fixture.tar'
            with tarfile.open(archive, 'w') as tar:
                entry = tarfile.TarInfo('.')
                entry.type = tarfile.DIRTYPE
                tar.addfile(entry)
                entry = tarfile.TarInfo('./usr/include/sample.h')
                entry.size = 4
                tar.addfile(entry, io.BytesIO(b'test'))
                entry = tarfile.TarInfo('./usr/lib/optional.so')
                entry.type = tarfile.SYMTYPE
                entry.linkname = 'optional.so.1'
                tar.addfile(entry)
            result = m.extract(archive, root / 'out')
            self.assertEqual(result['symbolic_links'], 1)
            self.assertEqual((root / 'out/usr/include/sample.h').read_bytes(), b'test')
            self.assertTrue((root / 'out/usr/lib/optional.so').is_symlink())

    def test_escape_refused_before_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'fixture.tar'
            with tarfile.open(archive, 'w') as tar:
                entry = tarfile.TarInfo('lib/unsafe')
                entry.type = tarfile.SYMTYPE
                entry.linkname = '../../escape'
                tar.addfile(entry)
            with self.assertRaises(ValueError):
                m.extract(archive, root / 'out')
            self.assertFalse((root / 'out').exists())
