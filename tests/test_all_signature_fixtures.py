import json
from pathlib import Path
import re
import unittest


class AllSignatureFixtures(unittest.TestCase):
    def test_fixture_sequences_match_original_config_exactly(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'tests/fixtures/d8-all-signatures.js').read_text()
        sequences = json.loads(re.search(r'var signatures = (.*);', source).group(1))
        active = json.loads((root / 'config/original.json').read_text())['active']
        self.assertEqual(len(sequences), 12)
        self.assertEqual(len(set(tuple(s) for s in sequences)), 12)
        for entry in active:
            self.assertEqual(sequences[entry['counter']], entry['opcodes'])
            key = 0
            for opcode in sequences[entry['counter']]:
                key = key * 123 + opcode - 0x45
            self.assertEqual(key, entry['key'])
