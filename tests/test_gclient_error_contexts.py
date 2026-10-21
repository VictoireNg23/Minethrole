import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('error_contexts', Path(__file__).resolve().parents[1] / 'scripts/show-gclient-errors.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ErrorContexts(unittest.TestCase):
    def test_first_error_and_overlapping_contexts(self):
        lines = ['progress\n'] * 8 + ['fatal: missing repository\n', 'Traceback (most recent call last):\n'] + ['progress\n'] * 100 + ['Finished.\n']
        result = [(n, s) for n, s in module.contexts(iter(lines)) if n is not None]
        self.assertIn((9, lines[8]), result)
        self.assertEqual(len(result), len(set(n for n, _ in result)))
        self.assertNotIn((111, 'Finished.\n'), result)

    def test_limit_reports_omitted_matches(self):
        result = list(module.contexts(iter(['fatal: failure\n'] * 100), radius=0, limit=2))
        self.assertEqual([n for n, _ in result if n is not None], [1, 2])
        self.assertIn('100', result[-1][1])
