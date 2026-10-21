import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('guarded_sync', ROOT / 'scripts/sync-chromium71-nohooks.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class PreservationDriverTests(unittest.TestCase):
    def test_only_exact_mirror_override_is_accepted(self):
        solution = [{'name': 'src', 'url': 'https://chromium.googlesource.com/chromium/src.git',
                     'managed': False, 'custom_deps': {'src/third_party/devtools-node-modules': sync.DEVTOOLS_MIRROR + '@' + sync.DEVTOOLS}, 'custom_vars': {}}]
        sync.validate_solution('solutions = ' + repr(solution), mirrored=True)
        with self.assertRaises(ValueError):
            sync.validate_solution('solutions = ' + repr(solution))
        solution[0]['custom_deps']['src/third_party/devtools-node-modules'] = sync.DEVTOOLS_MIRROR + '@HEAD'
        with self.assertRaises(ValueError):
            sync.validate_solution('solutions = ' + repr(solution), mirrored=True)

    def test_guard_blocks_recovery_and_retains_original_error(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            marker = root / 'must-not-move-or-delete'
            scm = root / 'gclient_scm.py'
            scm.write_text("class gclient_utils:\n    class Error(RuntimeError): pass\nclass SCMWrapper:\n    checkout_path = '/original/path'\n    def _DeleteOrMove(self, force):\n        open(" + repr(str(marker)) + ", 'w').write('BAD')\n")
            original = scm.read_bytes()
            entry = root / 'gclient.py'
            entry.write_text("import gclient_scm, sys\nassert sys.argv[1] == '--gclientfile=.gclient.minethrottle-mirror'\ntry:\n    raise ValueError('initial clone failure')\nexcept ValueError:\n    gclient_scm.SCMWrapper()._DeleteOrMove(False)\n")
            driver = root / 'driver.py'
            driver.write_text(sync.PRESERVATION_DRIVER)
            result = subprocess.run([sys.executable, '-B', str(driver), str(root), '--gclientfile=.gclient.minethrottle-mirror', 'sync'], capture_output=True, text=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('MINETHROTTLE_PRESERVATION_GUARD=enabled', result.stdout)
            self.assertIn('initial clone failure', result.stderr)
            self.assertIn('automatic delete/move refused', result.stderr)
            self.assertFalse(marker.exists())
            self.assertEqual(scm.read_bytes(), original)

    def test_guard_allows_normal_help_delegation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'gclient_scm.py').write_text('class SCMWrapper:\n    def _DeleteOrMove(self, force): pass\n')
            (root / 'gclient.py').write_text("import sys\nassert sys.argv[1:] == ['sync', '--help']\nprint('Usage: gclient sync commands')\n")
            driver = root / 'driver.py'
            driver.write_text(sync.PRESERVATION_DRIVER)
            result = subprocess.run([sys.executable, '-B', str(driver), str(root), 'sync', '--help'], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Usage: gclient', result.stdout)


if __name__ == '__main__':
    unittest.main()
