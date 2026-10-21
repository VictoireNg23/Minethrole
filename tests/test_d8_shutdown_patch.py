from pathlib import Path
import unittest


class ShutdownPatch(unittest.TestCase):
    def test_stop_precedes_collection_and_only_changes_shell(self):
        root = Path(__file__).resolve().parents[1]
        patch = (root / 'patches/chromium71/d8-stop-timer-before-teardown.patch').read_text()
        self.assertEqual([s for s in patch.splitlines() if s.startswith('+++ ')], ['+++ b/src/d8.cc'])
        self.assertLess(patch.index('sigaction(SIGALRM'), patch.index('setitimer(ITIMER_REAL'))
        self.assertLess(patch.index('setitimer(ITIMER_REAL'), patch.index('// Shut down contexts'))
        self.assertIn('SIG_IGN', patch)
