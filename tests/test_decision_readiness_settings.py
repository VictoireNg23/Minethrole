import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('readiness', ROOT / 'scripts/inspect-chromium71-decision-readiness.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DecisionSettings(unittest.TestCase):
    def test_extracts_original_patch_without_enabling_defense(self):
        source = '\n'.join(line[1:] for line in (ROOT / 'patches/v8.patch').read_text().splitlines()
                           if line.startswith('+') and not line.startswith('+++'))
        observed = module.settings(source)
        config = json.loads((ROOT / 'config/original.json').read_text())
        self.assertFalse(observed['defensive_enabled'])
        self.assertEqual(observed['interval_cpu_ms'], 500)
        self.assertEqual(observed['baseline_value'], config['means'])
        self.assertEqual(observed['baseline_stddev'], config['stddev'])
        self.assertEqual(observed['baseline_normalized'], config['normalized'])
        with self.assertRaises(ValueError):
            module.settings(source.replace('is_defensive = false', 'is_defensive = unknown'))
