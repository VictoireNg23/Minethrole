import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('toolchain_download', Path(__file__).resolve().parents[1] / 'scripts/download-chromium71-toolchain.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ToolchainIntegrity(unittest.TestCase):
    def test_expected_digest_is_enforced(self):
        m.verify_sha1('a', 'a')
        m.verify_sha1('a', None)
        with self.assertRaises(ValueError):
            m.verify_sha1('wrong', 'expected')
