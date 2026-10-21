import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_tools', ROOT / 'scripts/prepare-historical-depot-tools.py')
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


class PrepareToolsTests(unittest.TestCase):
    def test_snapshot_and_launchers_preserve_source(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            repo = parent / 'repo'
            repo.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', '-C', str(repo), *args], text=True, stderr=subprocess.DEVNULL).strip()
            git('init')
            (repo / 'gclient').write_text('historical\n')
            git('add', 'gclient')
            git('commit', '-m', 'old')
            old = git('rev-parse', 'HEAD')
            (repo / 'gclient').write_text('modern\n')
            git('commit', '-am', 'new')
            modern = git('rev-parse', 'HEAD')
            (repo / 'gclient').write_text('local changes\n')
            index = (repo / '.git/index').read_bytes()
            export = tools.export_snapshot(repo, old, parent)
            self.assertEqual((export / 'depot_tools/gclient').read_text(), 'historical\n')
            self.assertFalse((export / 'depot_tools/.git').exists())
            tools.write_launchers(export, repo, Path('/usr/bin/python3'), Path('/usr/bin/true'))
            result = subprocess.run([str(export / 'with-env.sh'), 'python', '-c', 'import os; print(os.environ["DEPOT_TOOLS_UPDATE"])'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), '0')
            self.assertEqual(git('rev-parse', 'HEAD'), modern)
            self.assertEqual((repo / 'gclient').read_text(), 'local changes\n')
            self.assertEqual((repo / '.git/index').read_bytes(), index)


if __name__ == '__main__':
    unittest.main()
