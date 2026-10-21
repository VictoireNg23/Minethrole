import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('devtools_diagnostic', ROOT / 'scripts/diagnose-devtools-dependency.py')
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)


class DevtoolsDiagnosticTests(unittest.TestCase):
    def test_broken_link_is_reported_without_modification(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'devtools-node-modules'
            path.symlink_to('missing-target')
            result = diag.describe(path)
            self.assertTrue(result['lexists'])
            self.assertFalse(result['target_exists'])
            self.assertEqual(result['symlink_target'], 'missing-target')
            self.assertTrue(path.is_symlink())

    def test_entries_is_not_executed_and_log_keeps_trigger(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            marker = root / 'never-create'
            value = diag.entries_value("open(" + repr(str(marker)) + ", 'w')\nentries = {'src/third_party/devtools-node-modules': 'expected'}", diag.DEPENDENCY)
            self.assertEqual(value, 'expected')
            self.assertFalse(marker.exists())
            log = root / 'sync.log'
            log.write_text('context\nURL changed for devtools-node-modules\n_DeleteOrMove\n')
            result = diag.log_context(log)
            self.assertTrue(any('URL changed' in row['text'] for row in result))


if __name__ == '__main__':
    unittest.main()
