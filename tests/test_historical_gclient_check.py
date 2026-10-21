import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gclient_check', ROOT / 'scripts/check-historical-gclient.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class GclientCheckTests(unittest.TestCase):
    def fixture(self, root, body):
        (root / 'provenance.json').write_text(json.dumps({'revision': checker.REVISION}))
        (root / 'depot_tools').mkdir()
        launcher = root / 'with-env.sh'
        launcher.write_text('#!/bin/sh\nexport DEPOT_TOOLS_UPDATE=0\nexec "$@"\n')
        launcher.chmod(0o755)
        executable = root / 'depot_tools/gclient'
        executable.write_text('#!/bin/sh\n' + body)
        executable.chmod(0o755)

    def run_case(self, body, timeout=5):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root, body)
            before = (root / 'depot_tools/gclient').read_bytes()
            with patch.dict(os.environ, {'VPYTHON_BYPASS': ''}), contextlib.redirect_stdout(io.StringIO()):
                result = checker.check(root, timeout)
            logs = Path(result['cwd'])
            self.assertEqual(json.loads((logs / 'result.json').read_text())['status'], result['status'])
            self.assertEqual((root / 'depot_tools/gclient').read_bytes(), before)
            return result

    def test_help_is_run_in_new_directory(self):
        result = self.run_case('test "$1" = --help || exit 8\ntest "$DEPOT_TOOLS_UPDATE" = 0 || exit 9\necho "Usage: gclient commands"\n')
        self.assertEqual(result['status'], 'help_completed')
        self.assertEqual(result['underlying_exit_code'], 0)

    def test_failures_and_empty_success_are_not_validated(self):
        self.assertEqual(self.run_case('exit 7\n')['underlying_exit_code'], 7)
        self.assertEqual(self.run_case('exit 7\n')['status'], 'failed')
        self.assertEqual(self.run_case('exit 0\n')['status'], 'help_output_not_recognized')

    def test_timeout_is_explicit(self):
        result = self.run_case('exec sleep 30\n', 0.1)
        self.assertEqual(result['status'], 'timeout')
        self.assertNotEqual(result['underlying_exit_code'], 0)


if __name__ == '__main__':
    unittest.main()
