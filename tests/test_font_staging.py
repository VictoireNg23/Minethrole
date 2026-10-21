import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('fonts_stage', Path(__file__).resolve().parents[1] / 'scripts/prepare-chromium71-test-fonts.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class TestFonts(unittest.TestCase):
    def test_extract_font_and_refuse_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'font.tar'
            with tarfile.open(archive, 'w') as tar:
                entry = tarfile.TarInfo('test_fonts/Ahem.ttf')
                entry.size = 4
                tar.addfile(entry, io.BytesIO(b'font'))
            m.extract_fonts(archive, root / 'out')
            self.assertEqual((root / 'out/test_fonts/Ahem.ttf').read_bytes(), b'font')
            with tarfile.open(archive, 'w') as tar:
                entry.type = tarfile.SYMTYPE
                entry.linkname = '../../outside'
                tar.addfile(entry)
            with self.assertRaises(ValueError):
                m.extract_fonts(archive, root / 'refused')
            self.assertFalse((root / 'refused').exists())
