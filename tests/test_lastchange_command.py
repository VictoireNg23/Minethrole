import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('lastchange_prepare', Path(__file__).resolve().parents[1] / 'scripts/prepare-chromium71-lastchange.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class LastchangeCommand(unittest.TestCase):
    def test_source_and_output_are_explicit(self):
        root = Path('/tmp/workspace with spaces')
        output = root / 'stage/LASTCHANGE'
        args = m.command(root, output)
        self.assertEqual(args[-4:], ['-s', str(root / 'src'), '-o', str(output)])
        self.assertEqual(args[1], 'python')
