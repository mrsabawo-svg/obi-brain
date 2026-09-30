import sys
import types
import unittest

import numpy as np


sys.modules.setdefault("yfinance", types.SimpleNamespace(Ticker=None))
hmm_module = types.ModuleType("hmmlearn.hmm")
hmm_module.GaussianHMM = object
sys.modules.setdefault("hmmlearn", types.ModuleType("hmmlearn"))
sys.modules.setdefault("hmmlearn.hmm", hmm_module)

from brain.brain_clean import compute_kelly, compute_obi, derive_sentiment


class BrainCalculationTests(unittest.TestCase):
    def test_obi_classifies_up_volume_as_bullish(self):
        closes = np.arange(1, 22, dtype=float)
        score, direction = compute_obi(closes, np.ones(21))
        self.assertEqual((score, direction), (100.0, "BULLISH"))

    def test_obi_handles_missing_volume_signal(self):
        score, direction = compute_obi(np.arange(20), np.zeros(20))
        self.assertEqual((score, direction), (50.0, "NEUTRAL"))

    def test_kelly_is_non_negative_and_capped(self):
        self.assertEqual(compute_kelly(0.5, 1, 0), 0.0)
        self.assertEqual(compute_kelly(1, 100, 1), 0.02)

    def test_volatile_regime_always_stands_aside(self):
        self.assertEqual(derive_sentiment("VOLATILE", "BULLISH"), "STAND ASIDE")


if __name__ == "__main__":
    unittest.main()
