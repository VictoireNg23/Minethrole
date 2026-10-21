import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sync_timeout', ROOT / 'scripts/diagnose-sync-timeout.py')
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class TimeoutDiagnosticTests(unittest.TestCase):
    def test_progress_noise_does_not_hide_initial_fetch(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sync.log'
            path.write_text("running git fetch origin\n" + '[0:59:30] Still working on:\n[0:59:30]   src\n' * 500)
            before = path.read_bytes()
            report = diagnostic.inspect_log(path)
            self.assertEqual(report['last_non_heartbeat_lines'], ['running git fetch origin'])
            self.assertEqual(report['operation_lines'], ['running git fetch origin'])
            self.assertEqual(report['line_count'], 1001)
            self.assertEqual(before, path.read_bytes())


if __name__ == '__main__':
    unittest.main()
