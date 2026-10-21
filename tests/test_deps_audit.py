import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('deps_audit', ROOT / 'scripts/audit-chromium71-deps.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class DepsAuditTests(unittest.TestCase):
    def test_var_concat_conditions_and_cipd(self):
        rows = audit.Reader("""
vars = {'host': 'https://example.invalid', 'rev': 'a'*40}
deps = {'src/a': Var('host') + '/a@' + Var('rev'),
        'src/b': {'dep_type': 'cipd', 'condition': 'checkout_win', 'packages': []}}
""".replace("'a'*40", repr('a' * 40))).rows()
        self.assertEqual(rows[0]['definition'], 'https://example.invalid/a@' + 'a' * 40)
        self.assertEqual(rows[1]['definition']['condition'], 'checkout_win')

    def test_unknown_expressions_are_not_executed(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'marker'
            text = "deps = {'src/a': open(" + repr(str(marker)) + ", 'w')}"
            rows = audit.Reader(text).rows()
            self.assertIn('unresolved', rows[0])
            self.assertFalse(marker.exists())

    def test_extra_mutation_is_not_silently_ignored(self):
        with self.assertRaises(ValueError):
            audit.Reader("deps = {}\ndeps.update({'src/a': 'url'})").rows()


if __name__ == '__main__':
    unittest.main()
