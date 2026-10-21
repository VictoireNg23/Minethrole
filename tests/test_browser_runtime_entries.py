import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('browser_stage', Path(__file__).resolve().parents[1] / 'scripts/stage-chromium71-browser-test.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RuntimeEntries(unittest.TestCase):
    def test_copy_runtime_without_build_objects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('chrome', 'icudtl.dat', 'v8_context_snapshot.bin', 'resources.pak', 'build.ninja', 'args.gn'):
                (root / name).write_text('fixture')
            for name in ('obj', 'gen', 'locales'):
                (root / name).mkdir()
            self.assertEqual({p.name for p in m.runtime_entries(root)}, {'chrome', 'icudtl.dat', 'v8_context_snapshot.bin', 'resources.pak', 'locales'})
