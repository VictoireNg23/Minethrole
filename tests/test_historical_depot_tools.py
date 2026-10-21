import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/inspect-historical-depot-tools.sh'


class HistoricalDepotToolsTests(unittest.TestCase):
    def test_selects_old_commit_without_checking_it_out(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            def git(*args, date=None):
                env = os.environ.copy()
                if date:
                    env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
                return subprocess.check_output(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', '-C', str(repo), *args], env=env, text=True, stderr=subprocess.DEVNULL).strip()
            git('init')
            marker = repo / 'must-not-execute'
            wrapper = repo / 'gclient'
            wrapper.write_text('#!/bin/sh\ntouch ' + str(marker) + '\n# python2\n')
            git('add', 'gclient')
            git('commit', '-m', 'old tools', date='2018-12-12T12:00:00Z')
            old = git('rev-parse', 'HEAD')
            wrapper.write_text('#!/bin/sh\n# python3 modern\n')
            git('commit', '-am', 'modern tools', date='2026-10-20T12:00:00Z')
            current = git('rev-parse', 'HEAD')
            wrapper.write_text('# user changes\n')
            index = (repo / '.git/index').read_bytes()
            result = subprocess.run(['bash', str(SCRIPT), str(repo)], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Candidate SHA (compatibility NOT validated): ' + old, result.stdout)
            self.assertEqual(git('rev-parse', 'HEAD'), current)
            self.assertEqual(wrapper.read_text(), '# user changes\n')
            self.assertEqual((repo / '.git/index').read_bytes(), index)
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
