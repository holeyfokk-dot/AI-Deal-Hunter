import unittest
from datetime import datetime

from agents.merchant import Merchant
from models.deal_result import DealResult
from tools.retailer_url import is_google_url


class TestDealResult(unittest.TestCase):
    def test_to_dict(self):
        result = DealResult(
            id="deal-1",
            specialist="Merchant",
            product_name="Test Game",
            current_price=19.99,
            historical_lowest_price=14.99,
            discount_percent=25.0,
            store="Steam",
            store_reputation="Trusted",
            platform="PC",
            drm="Steam",
            region_lock=None,
            bundle_included=False,
            url="https://www.steampowered.com/app/1",
            retailer_url="https://store.steampowered.com/app/1",
            deal_score=4.5,
            confidence_score=0.92,
            timestamp=datetime(2026, 7, 28, 12, 0, 0),
        )

        serialized = result.to_dict()
        self.assertEqual(serialized["product_name"], "Test Game")
        self.assertEqual(serialized["current_price"], 19.99)
        self.assertEqual(serialized["discount_percent"], 25.0)
        self.assertEqual(serialized["url"], "https://www.steampowered.com/app/1")
        self.assertEqual(serialized["retailer_url"], "https://store.steampowered.com/app/1")
        self.assertEqual(serialized["timestamp"], "2026-07-28T12:00:00")


class TestMerchant(unittest.TestCase):
    def test_handle_returns_deal_results(self):
        merchant = Merchant()
        request = {"query": "cyberpunk"}
        response = merchant.handle(request)

        self.assertIn("query", response)
        self.assertEqual(response["query"], "cyberpunk")
        self.assertIn("deals", response)
        self.assertIsInstance(response["deals"], list)

        for deal in response["deals"]:
            self.assertIsInstance(deal, DealResult)
            self.assertIsInstance(deal.product_name, str)
            self.assertIsInstance(deal.current_price, float)
            self.assertTrue(deal.deal_score >= 0)
            self.assertTrue(0.0 <= deal.confidence_score <= 1.0)
            # URLs must never be Google Shopping links.
            self.assertFalse(is_google_url(deal.url))
            self.assertFalse(is_google_url(deal.retailer_url))

    def test_can_handle_search(self):
        merchant = Merchant()
        self.assertTrue(merchant.can_handle("search"))
        self.assertTrue(merchant.can_handle("compare_prices"))
        self.assertFalse(merchant.can_handle("unknown_capability"))


if __name__ == "__main__":
    unittest.main()
