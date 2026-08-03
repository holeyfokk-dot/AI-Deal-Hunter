import unittest

from tools import retailer_url
from tools.retailer_url import (
    homepage_for,
    is_google_url,
    is_valid_product_url,
    resolve_item_url,
    strip_tracking,
    _pick_store_link,
)


class TestStripTracking(unittest.TestCase):
    def test_removes_tracking_params(self):
        url = (
            "https://www.newegg.com/p/N82E16814126758?item=N82E16814126758"
            "&utm_source=google&utm_medium=organic&utm_campaign=knc&srsltid=AfmBOo&tag=aff1"
        )
        cleaned = strip_tracking(url)
        self.assertIn("item=N82E16814126758", cleaned)
        for junk in ("utm_source", "utm_medium", "utm_campaign", "srsltid", "tag="):
            self.assertNotIn(junk, cleaned)

    def test_keeps_functional_params_and_handles_no_query(self):
        self.assertEqual(
            strip_tracking("https://www.walmart.com/ip/123?selectedSellerId=0"),
            "https://www.walmart.com/ip/123?selectedSellerId=0",
        )
        self.assertEqual(strip_tracking("https://x.com/p/1"), "https://x.com/p/1")


class TestValidProductURL(unittest.TestCase):
    def test_accepts_product_pages(self):
        self.assertTrue(is_valid_product_url("https://www.walmart.com/ip/PS5/123"))
        self.assertTrue(is_valid_product_url("https://www.bestbuy.com/site/x/6646420.p"))

    def test_rejects_homepage_search_google_and_http(self):
        self.assertFalse(is_valid_product_url("https://www.walmart.com"))          # homepage
        self.assertFalse(is_valid_product_url("https://www.amazon.com/s?k=rtx"))   # search
        self.assertFalse(is_valid_product_url("https://www.google.com/search?q=x"))  # google
        self.assertFalse(is_valid_product_url("http://www.walmart.com/ip/123"))    # not https


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
