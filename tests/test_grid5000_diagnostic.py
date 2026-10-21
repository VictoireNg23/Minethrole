"""Synthetic repositories only: no Chromium download or build required."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/diagnose-grid5000-chromium71.sh'


def git(root, *args):
    return subprocess.check_output(
        ['git', '-c', 'user.name=Diagnostic Test', '-c', 'user.email=test@example.invalid', '-C', str(root), *args],
        stderr=subprocess.DEVNULL, text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DiagnosticTests(unittest.TestCase):
    def test_syntax(self):
        subprocess.run(['bash', '-n', str(SCRIPT)], check=True)

    def test_missing_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(['bash', str(SCRIPT), str(Path(folder) / 'absent')], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((Path(folder) / 'absent').exists())

    def test_historical_objects_without_changing_worktrees(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            src = base / 'chromium71/src'
            v8 = src / 'v8'
            v8.mkdir(parents=True)
            git(v8, 'init')
            (v8 / 'include').mkdir()
            header = v8 / 'include/v8-version.h'
            header.write_text('#define V8_MAJOR_VERSION 7\n#define V8_MINOR_VERSION 1\n#define V8_BUILD_NUMBER 302\n#define V8_PATCH_LEVEL 31\n')
            git(v8, 'add', 'include/v8-version.h')
            git(v8, 'commit', '-m', 'synthetic historical V8')
            expected = git(v8, 'rev-parse', 'HEAD')
            header.write_text('#define V8_MAJOR_VERSION 15\n')
            git(v8, 'commit', '-am', 'synthetic current V8')
            git(src, 'init')
            (src / 'DEPS').write_text("vars = {'v8_revision': '" + expected + "'}\n")
            git(src, 'add', 'DEPS')
            git(src, 'commit', '-m', 'synthetic historical Chromium')
            git(src, 'tag', '71.0.3578.98')
            (src / 'DEPS').write_text('vars = {}\n')
            git(src, 'commit', '-am', 'synthetic current Chromium')
            # Existing local changes must survive, and .gclient must not execute.
            (src / 'DEPS').write_text('local user change\n')
            marker = base / 'must-not-be-created'
            (base / 'chromium71/.gclient').write_text(
                f"open({str(marker)!r}, 'w').write('BAD')\nsolutions = [{{'name': 'src', 'url': 'https://user:SECRET@example.invalid/repo?TOKEN=secret'}}]\n")
            watched = [src / 'DEPS', src / '.git/index', v8 / '.git/index', header]
            before = {p: digest(p) for p in watched}
            heads = [git(p, 'rev-parse', 'HEAD') for p in (src, v8)]
            result = subprocess.run(['bash', str(SCRIPT), str(base)], text=True, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Historical Chromium tag resolves locally:', result.stdout)
            self.assertIn('Expected V8 commit from historical Chromium DEPS: ' + expected, result.stdout)
            self.assertIn('#define V8_MAJOR_VERSION 7', result.stdout)
            self.assertIn('worktree not at the expected historical revision', result.stdout)
            self.assertIn('Not requested. Re-run with --network', result.stdout)
            self.assertNotIn('SECRET', result.stdout)
            self.assertNotIn('TOKEN=secret', result.stdout)
            self.assertFalse(marker.exists())
            self.assertEqual(before, {p: digest(p) for p in watched})
            self.assertEqual(heads, [git(p, 'rev-parse', 'HEAD') for p in (src, v8)])


if __name__ == '__main__':
    unittest.main()
