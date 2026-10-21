import hashlib
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('historical_gn', Path(__file__).resolve().parents[1] / 'scripts/prepare-chromium71-gn.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class HistoricalGn(unittest.TestCase):
    def test_integrity_gate(self):
        data = b'historical artifact fixture'
        expected = hashlib.sha1(data).hexdigest()
        m.verify(data, expected)
        with self.assertRaises(ValueError):
            m.verify(data + b'changed', expected)
