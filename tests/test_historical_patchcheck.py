"""Exercise historical blob checks with tiny synthetic repositories only."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('patchcheck', ROOT / 'scripts/check-chromium71-patches.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
PATCH = b'diff --git a/file.cc b/file.cc\n--- a/file.cc\n+++ b/file.cc\n@@ -1 +1 @@\n-old\n+new\n'


def git(root, *args):
    return subprocess.check_output(['git', '-c', 'user.name=Test', '-c',
        'user.email=test@example.invalid', '-C', str(root), *args], stderr=subprocess.DEVNULL, text=True).strip()


class HistoricalPatchChecks(unittest.TestCase):
    def test_paths_reject_traversal(self):
        with self.assertRaises(ValueError):
            checker.touched_paths(PATCH.replace(b'file.cc', b'../file.cc'))

    def test_original_paths(self):
        self.assertEqual(len(checker.touched_paths((ROOT / 'patches/v8.patch').read_bytes())), 9)
        self.assertEqual(len(checker.touched_paths((ROOT / 'patches/content.patch').read_bytes())), 1)

    def test_checks_old_content_without_modifying_current_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / 'repo'
            repo.mkdir()
            git(repo, 'init')
            (repo / 'file.cc').write_text('old\n')
            git(repo, 'add', 'file.cc')
            git(repo, 'commit', '-m', 'historical')
            rev = git(repo, 'rev-parse', 'HEAD')
            (repo / 'file.cc').write_text('modern\n')
            git(repo, 'commit', '-am', 'modern')
            (repo / 'file.cc').write_text('user changes\n')
            index_hash = hashlib.sha256((repo / '.git/index').read_bytes()).hexdigest()
            head = git(repo, 'rev-parse', 'HEAD')
            checker.extract_and_check(repo, rev, '', PATCH, root / 'export', 10)
            self.assertEqual((root / 'export/file.cc').read_text(), 'old\n')
            self.assertEqual((repo / 'file.cc').read_text(), 'user changes\n')
            self.assertEqual(git(repo, 'rev-parse', 'HEAD'), head)
            self.assertEqual(hashlib.sha256((repo / '.git/index').read_bytes()).hexdigest(), index_hash)
            with self.assertRaises(RuntimeError):
                checker.extract_and_check(repo, head, '', PATCH, root / 'mismatch', 10)
            self.assertEqual((root / 'mismatch/file.cc').read_text(), 'modern\n')
            with self.assertRaises(FileExistsError):
                checker.extract_and_check(repo, rev, '', PATCH, root / 'export', 10)


if __name__ == '__main__':
    unittest.main()
