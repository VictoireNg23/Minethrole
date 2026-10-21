import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sync_nohooks', ROOT / 'scripts/sync-chromium71-nohooks.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SyncNoHooksTests(unittest.TestCase):
    def test_pinned_args_exclude_destructive_options(self):
        args = sync.sync_arguments()
        for flag in ('--nohooks', '--noprehooks', '--jobs=4', 'src@' + sync.CHROMIUM, 'src/v8@' + sync.V8):
            self.assertIn(flag, args)
        for flag in ('--force', '--reset', '--delete_unversioned_trees'):
            self.assertNotIn(flag, args)

    def test_solution_configuration_is_not_executed(self):
        with self.assertRaises(ValueError):
            sync.validate_solution("import os\nsolutions = []")
        with self.assertRaises(ValueError):
            sync.validate_solution("solutions = []")
        with self.assertRaises(ValueError):
            sync.validate_solution("solutions = __import__('os').getcwd()")

    def test_logs_preserve_failure_and_timeout(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with contextlib.redirect_stdout(io.StringIO()):
                result = sync.logged_command([sys.executable, '-c', 'print("diagnostic"); raise SystemExit(7)'], root, sync.environment(root), root / 'failure.log', 5)
                timed = sync.logged_command([sys.executable, '-c', 'import time; time.sleep(30)'], root, sync.environment(root), root / 'timeout.log', 0.1)
            self.assertEqual(result['underlying_exit_code'], 7)
            self.assertIn('diagnostic', (root / 'failure.log').read_text())
            self.assertEqual(timed['status'], 'timeout')
            self.assertNotEqual(timed['underlying_exit_code'], 0)


if __name__ == '__main__':
    unittest.main()
