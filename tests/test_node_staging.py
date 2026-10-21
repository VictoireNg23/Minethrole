import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('node_stage', Path(__file__).resolve().parents[1] / 'scripts/stage-chromium71-node.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NodeStaging(unittest.TestCase):
    def test_plain_archive_and_refused_external_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'test.tar'
            with tarfile.open(archive, 'w') as tar:
                item = tarfile.TarInfo('node_modules/package/test.js')
                item.size = 4
                tar.addfile(item, io.BytesIO(b'test'))
            stage = root / 'stage'
            stage.mkdir()
            m.extract_plain(archive, stage, 'node_modules')
            self.assertEqual((stage / item.name).read_bytes(), b'test')
            with tarfile.open(archive, 'w') as tar:
                item.name = 'node_modules/../../escape'
                tar.addfile(item, io.BytesIO(b'test'))
            with self.assertRaises(ValueError):
                m.extract_plain(archive, stage, 'node_modules')
            self.assertFalse((root / 'escape').exists())
