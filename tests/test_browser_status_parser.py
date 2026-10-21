import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('browser_ready', Path(__file__).resolve().parents[1] / 'scripts/test-chromium71-browser-ready.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ProcStatus(unittest.TestCase):
    def test_parse_renderer_security_fields(self):
        fields = m.parse_status('Name:\tchrome\nUid:\t998 998 998 998\nSeccomp:\t2\nNoNewPrivs:\t1\n')
        self.assertEqual(fields['Uid'], '998 998 998 998')
        self.assertEqual(fields['Seccomp'], '2')
        self.assertEqual(fields['NoNewPrivs'], '1')
