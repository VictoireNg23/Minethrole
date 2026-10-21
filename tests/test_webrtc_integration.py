import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('webrtc_integration', Path(__file__).resolve().parents[1] / 'scripts/integrate-webrtc-exact.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class WebrtcIntegration(unittest.TestCase):
    def test_local_import_and_refusal_of_untracked_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            def git(path, *args):
                return subprocess.check_output(['git', '-C', str(path)] + list(args), stderr=subprocess.DEVNULL, text=True).strip()
            git(source, 'init')
            (source / 'sample').write_text('historical fixture')
            git(source, 'add', 'sample')
            git(source, '-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-m', 'fixture')
            revision = git(source, 'rev-parse', 'HEAD')
            git(source, 'fetch', '.', revision)
            workspace = root / 'workspace'
            target = workspace / 'src/third_party/webrtc'
            target.mkdir(parents=True)
            (workspace / 'preparation.json').write_text('{}')
            git(target, 'init')
            report = root / 'fetch.json'
            report.write_text(json.dumps({'status': 'exact_commit_fetched_and_fsck_passed', 'revision': revision, 'repository': str(source)}))
            (target / 'keep').write_text('preserve')
            with patch.object(m, 'REVISION', revision), patch.object(sys, 'argv', ['script', str(workspace), str(report)]):
                self.assertEqual(m.main(), 1)
                self.assertEqual((target / 'keep').read_text(), 'preserve')
                # Remove only our own test fixture to exercise the clean path.
                (target / 'keep').unlink()
                self.assertEqual(m.main(), 0)
            self.assertEqual(git(target, 'rev-parse', 'HEAD'), revision)
            self.assertEqual((target / 'sample').read_text(), 'historical fixture')

    def test_no_checkout_clone_can_be_populated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            def git(path, *args):
                return subprocess.check_output(['git', '-C', str(path)] + list(args), stderr=subprocess.DEVNULL, text=True).strip()
            git(source, 'init')
            (source / 'sample').write_text('historical fixture')
            git(source, 'add', 'sample')
            git(source, '-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-m', 'fixture')
            revision = git(source, 'rev-parse', 'HEAD')
            git(source, 'fetch', '.', revision)
            workspace = root / 'workspace'
            target = workspace / 'src/third_party/webrtc'
            target.parent.mkdir(parents=True)
            subprocess.check_call(['git', 'clone', '--no-checkout', str(source), str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            (workspace / 'preparation.json').write_text('{}')
            self.assertEqual(git(target, 'ls-files', '--stage'), '')
            self.assertTrue(git(target, 'status', '--porcelain=v1').startswith('D  '))
            report = root / 'fetch.json'
            report.write_text(json.dumps({'status': 'exact_commit_fetched_and_fsck_passed', 'revision': revision, 'repository': str(source)}))
            with patch.object(m, 'REVISION', revision), patch.object(sys, 'argv', ['script', str(workspace), str(report)]):
                self.assertEqual(m.main(), 0)
            self.assertEqual((target / 'sample').read_text(), 'historical fixture')
            self.assertEqual(git(target, 'status', '--porcelain=v1'), '')
