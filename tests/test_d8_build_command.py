import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('d8_build', Path(__file__).resolve().parents[1] / 'scripts/build-chromium71-d8.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class D8BuildCommand(unittest.TestCase):
    def test_only_d8_bounded_jobs_stop_first_error(self):
        root = Path('/tmp/workspace with spaces')
        args = m.command(root, root / 'src/out/prepared', 8)
        self.assertEqual(args[1], '/usr/bin/ninja')
        self.assertEqual(args[-5:], ['-j', '8', '-k', '1', 'd8'])
        self.assertNotIn('chrome', args)

    def test_chrome_target_is_explicit_and_preserves_limits(self):
        root = Path('/tmp/isolated')
        args = m.command(root, root / 'src/out/prepared', 16, 'chrome')
        self.assertEqual(args[-5:], ['-j', '16', '-k', '1', 'chrome'])
