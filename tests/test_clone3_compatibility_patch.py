from pathlib import Path
import unittest


class Clone3Compatibility(unittest.TestCase):
    def test_narrow_errno_policy_and_native_regression(self):
        root = Path(__file__).resolve().parents[1]
        patch = (root / 'patches/chromium71/glibc-clone3-enosys.patch').read_text()
        added = '\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
        self.assertIn('kClone3X86_64 = 435', added)
        self.assertIn('return Error(ENOSYS)', added)
        self.assertNotIn('return Allow()', added)
        self.assertIn('defined(__x86_64__) && !defined(__ILP32__)', added)
        self.assertIn('Clone3ReturnsEnosys', added)
        self.assertIn('BPF_ASSERT_EQ(ENOSYS, errno)', added)
        self.assertEqual(len([line for line in patch.splitlines() if line.startswith('+++ ')]), 2)
