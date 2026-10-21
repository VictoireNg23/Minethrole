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

    def test_selects_renderer_without_proc_exe_access(self):
        binary = Path('/tmp/stage/browser/chrome')
        processes = [(40, str(binary) + ' --type=renderer --headless '),
                     (12, str(binary) + ' --headless '),
                     (22, str(binary) + ' --type=zygote '),
                     (99, str(binary) + '-other --type=renderer ')]
        self.assertEqual(m.select_debug_targets(processes, binary), [(12, 'browser'), (40, 'renderer')])
