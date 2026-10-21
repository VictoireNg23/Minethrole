import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('archive_inspection', ROOT / 'scripts/inspect-depot-tools-archive.py')
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)


class ArchiveInspectionTests(unittest.TestCase):
    def test_reports_links_without_following_or_extracting(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'archive.tar'
            with tarfile.open(path, 'w', format=tarfile.PAX_FORMAT, pax_headers={'comment': 'test-commit'}) as archive:
                link = tarfile.TarInfo('cbuildbot')
                link.type = tarfile.SYMTYPE
                link.linkname = '../external-command'
                archive.addfile(link)
                file = tarfile.TarInfo('../must-not-extract')
                file.size = 3
                archive.addfile(file, io.BytesIO(b'bad'))
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                inspector.inspect(path)
            self.assertIn("'cbuildbot' type: symlink target: '../external-command'", output.getvalue())
            self.assertIn('test-commit', output.getvalue())
            self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(list(root.iterdir()), [path])
            self.assertFalse((root.parent / 'must-not-extract').exists())


if __name__ == '__main__':
    unittest.main()
