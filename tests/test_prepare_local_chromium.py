import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_chromium', ROOT / 'scripts/prepare-chromium71-local.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LocalCloneTests(unittest.TestCase):
    def test_borrows_objects_and_preserves_modern_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source'
            source.mkdir()
            def git(repo, *args):
                return subprocess.check_output(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', '-C', str(repo), *args], text=True, stderr=subprocess.DEVNULL).strip()
            git(source, 'init')
            (source / 'code').write_text('old')
            git(source, 'add', 'code')
            git(source, 'commit', '-m', 'old')
            old = git(source, 'rev-parse', 'HEAD')
            (source / 'code').write_text('modern')
            git(source, 'commit', '-am', 'modern')
            current = git(source, 'rev-parse', 'HEAD')
            (source / 'code').write_text('user changes')
            index = (source / '.git/index').read_bytes()
            module.verify_source(source, old)
            target = root / 'new'
            with contextlib.redirect_stdout(io.StringIO()):
                record = module.clone_local(source, target, old, 'https://example.invalid/repo.git')
            self.assertEqual((target / 'code').read_text(), 'old')
            self.assertEqual(git(target, 'rev-parse', 'HEAD'), old)
            self.assertEqual(git(target, 'remote', 'get-url', 'origin'), 'https://example.invalid/repo.git')
            self.assertTrue(record['borrowed_object_stores'])
            self.assertEqual(git(source, 'rev-parse', 'HEAD'), current)
            self.assertEqual((source / 'code').read_text(), 'user changes')
            self.assertEqual((source / '.git/index').read_bytes(), index)
            with self.assertRaises(ValueError):
                module.clone_local(source, target, old, 'https://example.invalid/repo.git')


if __name__ == '__main__':
    unittest.main()
