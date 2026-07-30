import unittest

from tools import retailer_url
from tools.retailer_url import (
    homepage_for,
    is_google_url,
    resolve_item_url,
    _pick_store_link,
)


class TestIsGoogleURL(unittest.TestCase):
    def test_flags_google_shopping_urls(self):
        self.assertTrue(is_google_url("https://www.google.com/search?ibp=oshop&q=PS5"))
        self.assertTrue(is_google_url("https://shopping.google.com/product/123"))

    def test_allows_direct_retailer_urls(self):
        self.assertFalse(is_google_url("https://www.amazon.com/dp/B0ABC"))
        self.assertFalse(is_google_url("https://www.bestbuy.com/site/xyz"))
        self.assertFalse(is_google_url(None))


class TestHomepageFor(unittest.TestCase):
    def test_known_retailers(self):
        self.assertEqual(homepage_for("Amazon"), "https://www.amazon.com")
        self.assertEqual(homepage_for("Best Buy"), "https://www.bestbuy.com")
        self.assertEqual(homepage_for("Walmart - Seller"), "https://www.walmart.com")

    def test_unknown_retailer_returns_none(self):
        self.assertIsNone(homepage_for("Some Random Shop"))
        self.assertIsNone(homepage_for(None))


class TestPickStoreLink(unittest.TestCase):
    def test_prefers_store_matching_source(self):
        stores = [
            {"name": "Walmart", "link": "https://www.walmart.com/ip/123"},
            {"name": "Best Buy", "link": "https://www.bestbuy.com/site/456"},
        ]
        self.assertEqual(
            _pick_store_link(stores, "Best Buy"),
            "https://www.bestbuy.com/site/456",
        )

    def test_skips_google_links(self):
        stores = [
            {"name": "Google", "link": "https://www.google.com/shopping/x"},
            {"name": "Target", "link": "https://www.target.com/p/789"},
        ]
        self.assertEqual(_pick_store_link(stores, "Unknown"), "https://www.target.com/p/789")

    def test_returns_none_when_only_google(self):
        stores = [{"name": "Google", "link": "https://shopping.google.com/x"}]
        self.assertIsNone(_pick_store_link(stores, "Walmart"))


class TestResolveItemURL(unittest.TestCase):
    def test_uses_direct_link_on_item(self):
        item = {"source": "Amazon", "link": "https://www.amazon.com/dp/B0XYZ"}
        self.assertEqual(
            resolve_item_url(item, use_immersive=False),
            "https://www.amazon.com/dp/B0XYZ",
        )

    def test_ignores_google_product_link_and_falls_back_to_homepage(self):
        item = {
            "source": "Best Buy",
            "product_link": "https://www.google.com/search?ibp=oshop&q=x",
        }
        resolved = resolve_item_url(item, use_immersive=False)
        self.assertEqual(resolved, "https://www.bestbuy.com")
        self.assertFalse(is_google_url(resolved))

    def test_uses_immersive_direct_url_when_available(self):
        item = {
            "source": "Walmart",
            "immersive_product_page_token": "tok-123",
            "product_link": "https://www.google.com/search?q=x",
        }

        original = retailer_url.fetch_direct_url
        retailer_url.fetch_direct_url = (
            lambda token, source, api_key=None: "https://www.walmart.com/ip/999"
        )
        try:
            resolved = resolve_item_url(item, use_immersive=True)
        finally:
            retailer_url.fetch_direct_url = original

        self.assertEqual(resolved, "https://www.walmart.com/ip/999")
        self.assertFalse(is_google_url(resolved))


if __name__ == "__main__":
    unittest.main()
