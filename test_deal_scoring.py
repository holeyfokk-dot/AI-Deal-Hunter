import unittest

from tools.deal_scoring import (
    REP_FIRST_PARTY,
    REP_MARKETPLACE,
    REP_UNKNOWN,
    classify_retailer,
    detect_condition,
    is_accessory,
    market_average,
    score_item,
)

MARKET_AVG = 500.0


def _reasons_text(breakdown):
    return " ".join(breakdown.reasons).lower()


class TestClassifyRetailer(unittest.TestCase):
    def test_first_party_retailers(self):
        for name in ["Amazon", "Walmart", "Best Buy", "Target", "Costco",
                     "Newegg", "Micro Center", "B&H"]:
            self.assertEqual(classify_retailer(name), REP_FIRST_PARTY, name)

    def test_marketplace_third_party_sellers(self):
        self.assertEqual(classify_retailer("Walmart - Dealbuddy"), REP_MARKETPLACE)
        self.assertEqual(classify_retailer("Newegg.com - Hoengager"), REP_MARKETPLACE)
        self.assertEqual(classify_retailer("eBay"), REP_MARKETPLACE)

    def test_unknown_retailer(self):
        self.assertEqual(classify_retailer("Glocalzone"), REP_UNKNOWN)
        self.assertEqual(classify_retailer(None), REP_UNKNOWN)


class TestAccessoryDetection(unittest.TestCase):
    def test_accessories_flagged(self):
        self.assertTrue(is_accessory("PS5 DualSense Wireless Controller"))
        self.assertTrue(is_accessory("Xbox Series X Charging Dock"))
        self.assertTrue(is_accessory("Nintendo Switch Carrying Case"))

    def test_main_product_not_flagged(self):
        self.assertFalse(is_accessory("PlayStation 5 Console"))
        self.assertFalse(is_accessory("Nintendo Switch 2 Console with Cleaning Kit"))
        self.assertFalse(is_accessory("AMD Ryzen 7 7800X3D Processor"))


class TestConditionDetection(unittest.TestCase):
    def test_detects_conditions(self):
        self.assertEqual(detect_condition("Refurbished PlayStation 5"), "refurbished")
        self.assertEqual(detect_condition("PS5 for parts not working"), "for parts")
        self.assertEqual(detect_condition("Open Box PlayStation 5"), "open-box")

    def test_new_product_has_no_condition(self):
        self.assertIsNone(detect_condition("PlayStation 5 Console"))


class TestMarketAverage(unittest.TestCase):
    def test_median(self):
        self.assertEqual(market_average([100, 200, 300]), 200)
        self.assertIsNone(market_average([]))
        self.assertIsNone(market_average([0, -5]))


class TestScoreItem(unittest.TestCase):
    def _realistic_first_party(self):
        item = {"title": "PlayStation 5 Console", "price": "$420.00", "source": "Amazon"}
        return score_item(item, "playstation 5", MARKET_AVG)

    def test_realistic_first_party_scores_high(self):
        b = self._realistic_first_party()
        self.assertFalse(b.excluded)
        self.assertGreater(b.deal_score, 0.8)
        self.assertGreater(b.confidence_score, 0.7)
        self.assertEqual(b.reputation, REP_FIRST_PARTY)
        self.assertIn("first-party", _reasons_text(b))
        self.assertIn("below market", _reasons_text(b))

    def test_fake_lowball_price_is_flagged_not_rewarded(self):
        item = {"title": "PlayStation 5 Console", "price": "$28.00", "source": "Amazon"}
        b = score_item(item, "playstation 5", MARKET_AVG)
        self.assertFalse(b.excluded)  # kept, but must not rank high
        self.assertLess(b.deal_score, 0.3)
        self.assertLess(b.deal_score, self._realistic_first_party().deal_score)
        self.assertIn("unrealistically low", _reasons_text(b))

    def test_accessory_is_excluded(self):
        item = {"title": "PS5 DualSense Wireless Controller", "price": "$59.99", "source": "Amazon"}
        b = score_item(item, "playstation 5", MARKET_AVG)
        self.assertTrue(b.excluded)
        self.assertEqual(b.exclusion_reason, "accessory")

    def test_marketplace_seller_penalized_vs_first_party(self):
        base = {"title": "PlayStation 5 Console", "price": "$420.00"}
        first_party = score_item({**base, "source": "Best Buy"}, "playstation 5", MARKET_AVG)
        marketplace = score_item({**base, "source": "Walmart - Reseller"}, "playstation 5", MARKET_AVG)
        self.assertEqual(marketplace.reputation, REP_MARKETPLACE)
        self.assertLess(marketplace.deal_score, first_party.deal_score)
        self.assertIn("marketplace", _reasons_text(marketplace))

    def test_refurbished_penalized_unless_requested(self):
        item = {"title": "Refurbished PlayStation 5 Console", "price": "$420.00", "source": "Amazon"}
        not_requested = score_item(item, "playstation 5", MARKET_AVG)
        requested = score_item(item, "refurbished playstation 5", MARKET_AVG)
        self.assertLess(not_requested.deal_score, requested.deal_score)
        self.assertIn("penalized", _reasons_text(not_requested))

    def test_above_market_price_scores_lower_than_discount(self):
        cheap = {"title": "PlayStation 5 Console", "price": "$400.00", "source": "Amazon"}
        pricey = {"title": "PlayStation 5 Console", "price": "$650.00", "source": "Amazon"}
        self.assertGreater(
            score_item(cheap, "playstation 5", MARKET_AVG).deal_score,
            score_item(pricey, "playstation 5", MARKET_AVG).deal_score,
        )


if __name__ == "__main__":
    unittest.main()
