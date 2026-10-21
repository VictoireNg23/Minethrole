import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

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

    def test_new_mirror_is_not_enabled_or_inherited(self):
        with patch.dict(os.environ, {'GIT_CACHE_PATH': '/existing/cache'}):
            self.assertNotIn('GIT_CACHE_PATH', sync.environment(Path('/example')))
        self.assertIn('--verbose', sync.sync_arguments())

    def test_probe_requires_explicit_no_cache(self):
        self.assertEqual(sync.validate_cache_probe('MINETHROTTLE_CACHE_PROBE={"cache_path": null}'), {'cache_path': None})
        with self.assertRaises(ValueError):
            sync.validate_cache_probe('MINETHROTTLE_CACHE_PROBE={"cache_path": "/cache"}')
        with self.assertRaises(ValueError):
            sync.validate_cache_probe('')

    def test_probe_uses_historical_module_without_network(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            module = root / 'git_cache.py'
            module.write_text('class Mirror:\n    @staticmethod\n    def GetCachePath():\n        raise RuntimeError("not configured")\n')
            import subprocess
            result = subprocess.run([sys.executable, '-B', '-c', sync.CACHE_PROBE, str(root)], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(sync.validate_cache_probe(result.stdout)['cache_path'], None)

    def test_mirror_origin_is_not_silently_rewritten(self):
        with patch.object(sync.subprocess, 'check_output', return_value=b'/old/cache/mirror\n'):
            with self.assertRaises(ValueError):
                sync.check_origin(Path('/example/src'), 'https://example.invalid/src.git', {})

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
