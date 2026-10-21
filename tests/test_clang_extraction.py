import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('clang_stage', Path(__file__).resolve().parents[1] / 'scripts/stage-chromium71-clang.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ClangExtraction(unittest.TestCase):
    def test_internal_link_and_reject_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'fixture.tar'
            with tarfile.open(archive, 'w') as tar:
                file = tarfile.TarInfo('bin/clang')
                file.size = 4
                tar.addfile(file, io.BytesIO(b'test'))
                link = tarfile.TarInfo('bin/clang++')
                link.type = tarfile.SYMTYPE
                link.linkname = 'clang'
                tar.addfile(link)
            m.extract_clang(archive, root / 'out')
            self.assertEqual((root / 'out/bin/clang++').read_bytes(), b'test')
            with tarfile.open(archive, 'w') as tar:
                link.linkname = '../../escape'
                tar.addfile(link)
            with self.assertRaises(ValueError):
                m.extract_clang(archive, root / 'refused')
            self.assertFalse((root / 'refused').exists())
