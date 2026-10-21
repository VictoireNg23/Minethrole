import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('native_bpf', Path(__file__).resolve().parents[1] / 'scripts/test-chromium71-sandbox-native.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NativeBpfResults(unittest.TestCase):
    def test_zero_or_missing_tests_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tests.xml'
            path.write_text('<testsuites/>')
            self.assertFalse(m.read_test_results(path)[1])
            cases = ''.join('<testcase classname="BaselinePolicy" name="%s" status="run"/>' % name.split('.')[1] for name in m.EXPECTED)
            path.write_text('<testsuites><testsuite>' + cases + '</testsuite></testsuites>')
            self.assertTrue(m.read_test_results(path)[1])
            path.write_text(path.read_text().replace('status="run"/>', 'status="run"><failure/></testcase>', 1))
            self.assertFalse(m.read_test_results(path)[1])
