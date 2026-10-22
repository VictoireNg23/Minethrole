import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('decision_math', Path(__file__).resolve().parents[1] / 'scripts/check-original-decision-math.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DecisionMath(unittest.TestCase):
    def test_original_zero_norm_and_average_zscore(self):
        cosine, sigma = module.scores([0, 0, 0], [2, 4, 6], [1, 2, 3], [1, 0, 0])
        self.assertEqual(cosine, -1)
        self.assertEqual(sigma, -2)
        cosine, sigma = module.scores([3, 0, 0], [2, 4, 6], [1, 2, 3], [1, 0, 0])
        self.assertEqual(cosine, 1)
        self.assertEqual(sigma, -1)
