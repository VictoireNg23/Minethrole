import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('counter_smoke', Path(__file__).resolve().parents[1] / 'scripts/test-chromium71-counters.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CounterParser(unittest.TestCase):
    def test_headers_are_not_counter_rows(self):
        text = '1 123456.00 0\n' + ' '.join(map(str, [1, 2, 0, 0, 3, 4, 0, 0, 0, 0, 20000] + [0] * 11)) + '\n'
        self.assertEqual(m.parse_counters(text), [[20000] + [0] * 11])

    def test_signal_after_marker_cannot_pass(self):
        expected = [0] * 12
        self.assertFalse(m.case_passed(-11, True, expected, expected))
        self.assertFalse(m.case_passed(0, True, None, expected))
        self.assertTrue(m.case_passed(0, True, expected, expected))
