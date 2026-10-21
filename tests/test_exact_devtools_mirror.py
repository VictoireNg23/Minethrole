import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('exact_mirror', ROOT / 'scripts/prepare-devtools-exact-mirror.py')
mirror = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mirror)


class ExactMirrorTests(unittest.TestCase):
    def test_exact_commit_fetched_without_following_latest_or_changing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'mirror'
            source.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', '-C', str(source), *args], text=True, stderr=subprocess.DEVNULL).strip()
            git('init')
            (source / 'data').write_text('historical')
            git('add', 'data')
            git('commit', '-m', 'historical')
            expected = git('rev-parse', 'HEAD')
            (source / 'data').write_text('latest')
            git('commit', '-am', 'latest')
            latest = git('rev-parse', 'HEAD')
            logs = root / 'logs'
            logs.mkdir()
            target = root / 'dependency'
            with contextlib.redirect_stdout(io.StringIO()):
                actual = mirror.fetch_exact(target, str(source), expected, logs, 10)
            self.assertEqual(actual, expected)
            self.assertEqual((target / 'data').read_text(), 'historical')
            self.assertEqual(git('rev-parse', 'HEAD'), latest)
            self.assertEqual((source / 'data').read_text(), 'latest')
            with self.assertRaises(FileExistsError):
                mirror.fetch_exact(target, str(source), expected, logs, 10)

    def test_original_configuration_must_be_literal_and_unchanged(self):
        with self.assertRaises(ValueError):
            mirror.read_solution("import os\nsolutions = []")
        with self.assertRaises(ValueError):
            mirror.read_solution("solutions = []")


if __name__ == '__main__':
    unittest.main()
