import unittest

from tools.retailer_trust import (
    classify_tier,
    confidence_cap,
    is_trusted,
    rating_label,
    score_cap,
)
from tools.deal_scoring import score_item

MARKET_AVG = 500.0


class TestTierClassification(unittest.TestCase):
    def test_tiers(self):
        self.assertEqual(classify_tier("Best Buy"), 1)
        self.assertEqual(classify_tier("Amazon"), 1)
        self.assertEqual(classify_tier("AAAWave"), 2)
        self.assertEqual(classify_tier("eBay"), 3)
        self.assertEqual(classify_tier("Walmart - Reseller"), 3)  # marketplace seller
        self.assertEqual(classify_tier("TridgeConsulting"), 4)
        self.assertEqual(classify_tier("Serigrafia.eus"), 4)
        self.assertEqual(classify_tier(None), 4)

    def test_caps(self):
        self.assertEqual(score_cap("Best Buy"), 1.00)
        self.assertEqual(score_cap("AAAWave"), 0.90)
        self.assertEqual(score_cap("eBay"), 0.65)
        self.assertEqual(score_cap("UnknownShop"), 0.45)
        self.assertEqual(confidence_cap("UnknownShop"), 0.30)

    def test_is_trusted(self):
        self.assertTrue(is_trusted("Walmart"))
        self.assertTrue(is_trusted("Adorama"))
        self.assertFalse(is_trusted("eBay"))
        self.assertFalse(is_trusted("NeverHeardOfIt"))


class TestRatingLabels(unittest.TestCase):
    def test_unknown_never_amazing(self):
        self.assertEqual(rating_label(0.99, "TridgeConsulting"), "⚠️ Needs Verification")
        self.assertEqual(rating_label(0.99, "eBay"), "🟡 Potential Deal")

    def test_trusted_can_be_amazing(self):
        self.assertEqual(rating_label(0.9, "Best Buy"), "🔥 Amazing Deal")
        # Specialty (tier 2) tops out at "Great Deal", not "Amazing".
        self.assertEqual(rating_label(0.95, "AAAWave"), "✅ Great Deal")


class TestScoreCapIntegration(unittest.TestCase):
    def _score(self, source, price="$400"):
        return score_item({"title": "PlayStation 5 Console", "price": price, "source": source}, "playstation 5", MARKET_AVG)

    def test_unknown_cheap_store_cannot_outrank_trusted(self):
        # The reviewer's case: Best Buy $579 should beat RandomShop123 $549.
        trusted = self._score("Best Buy", "$579")
        unknown = self._score("RandomShop123", "$549")  # cheaper but unknown
        self.assertGreater(trusted.deal_score, unknown.deal_score)
        self.assertLessEqual(unknown.deal_score, 0.45)
        self.assertLessEqual(unknown.confidence_score, 0.30)

    def test_unknown_score_and_confidence_capped(self):
        b = self._score("Serigrafia.eus", "$400")  # would otherwise be a big discount
        self.assertLessEqual(b.deal_score, 0.45)
        self.assertLessEqual(b.confidence_score, 0.30)
        self.assertTrue(any("capped" in r.lower() for r in b.reasons))


if __name__ == "__main__":
    unittest.main()
