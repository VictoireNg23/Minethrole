import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('cpu_audit', Path(__file__).resolve().parents[1] / 'scripts/analyze-chromium71-synthetic-cpu.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CpuAudit(unittest.TestCase):
    def test_tracks_timespec_across_second_boundary(self):
        def row(sec, ns, count):
            return ' '.join(map(str, [1, 2, 0, 0, sec, ns] + [0]*4 + [count] + [0]*11))
        result = module.inspect_count('1 1000.0 0\n' + row(0, 999000000, 0) + '\n' + row(1, 1000000, 3))
        self.assertEqual(result['streams'][0]['cpu_span_ms'], 2)
        self.assertTrue(result['streams'][0]['cpu_advances'])
        reversed_result = module.inspect_count(row(1, 1000000, 3) + '\n' + row(0, 999000000, 0))
        self.assertFalse(reversed_result['streams'][0]['cpu_monotonic'])
        self.assertFalse(reversed_result['streams'][0]['counters_monotonic'])
