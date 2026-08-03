import unittest

from tools.product_dedup import (
    best_offer,
    canonical_product_key,
    consolidate_offers,
)


class TestCanonicalKey(unittest.TestCase):
    def test_same_product_id_same_key(self):
        a = {"title": "ASUS TUF RTX 5070 OC", "product_id": "123"}
        b = {"title": "Asus Tuf Gaming GeForce RTX 5070 O12G", "product_id": "123"}
        self.assertEqual(canonical_product_key(a), canonical_product_key(b))

    def test_different_product_id_different_key(self):
        a = {"title": "ASUS TUF RTX 5070", "product_id": "123"}
        b = {"title": "ASUS TUF RTX 5070", "product_id": "456"}
        self.assertNotEqual(canonical_product_key(a), canonical_product_key(b))

    def test_title_fallback_merges_same_brand_model(self):
        a = {"title": "ASUS TUF GeForce RTX 5070 OC Edition"}
        b = {"title": "ASUS TUF RTX 5070 Graphics Card"}
        self.assertEqual(canonical_product_key(a), canonical_product_key(b))

    def test_title_fallback_separates_brands(self):
        a = {"title": "ASUS TUF RTX 5070"}
        b = {"title": "PNY RTX 5070"}
        self.assertNotEqual(canonical_product_key(a), canonical_product_key(b))


class TestBestOffer(unittest.TestCase):
    def test_picks_cheapest_across_retailers(self):
        # The scenario from the request: one product, four retailer prices.
        offers = [
            {"title": "ASUS TUF RTX 5070 OC", "source": "Amazon", "price": "$589", "product_id": "p1"},
            {"title": "ASUS TUF RTX 5070 OC", "source": "Best Buy", "price": "$579", "product_id": "p1"},
            {"title": "ASUS TUF RTX 5070 OC", "source": "Newegg", "price": "$574", "product_id": "p1"},
            {"title": "ASUS TUF RTX 5070 OC", "source": "Walmart", "price": "$599", "product_id": "p1"},
        ]
        best, others = best_offer(offers, market_avg=585.0)
        self.assertEqual(best["source"], "Newegg")
        self.assertEqual(len(others), 3)
        self.assertEqual([o["store"] for o in others], ["Best Buy", "Amazon", "Walmart"])

    def test_skips_unrealistic_lowball_when_realistic_exists(self):
        offers = [
            {"title": "ASUS TUF RTX 5070", "source": "ScamShop", "price": "$40"},
            {"title": "ASUS TUF RTX 5070", "source": "Newegg", "price": "$574"},
            {"title": "ASUS TUF RTX 5070", "source": "Best Buy", "price": "$579"},
        ]
        best, _ = best_offer(offers, market_avg=575.0)
        self.assertEqual(best["source"], "Newegg")


class TestConsolidate(unittest.TestCase):
    def test_same_product_collapses_to_one_cluster(self):
        offers = [
            {"title": "ASUS TUF RTX 5070 OC", "source": "Amazon", "price": "$589", "product_id": "p1"},
            {"title": "ASUS TUF RTX 5070 OC", "source": "Newegg", "price": "$574", "product_id": "p1"},
            {"title": "ASUS TUF RTX 5070 OC", "source": "Walmart", "price": "$599", "product_id": "p1"},
        ]
        clusters = consolidate_offers(offers)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(next(iter(clusters.values()))), 3)

    def test_distinct_products_stay_separate(self):
        offers = [
            {"title": "ASUS TUF RTX 5070", "source": "Amazon", "price": "$589", "product_id": "p1"},
            {"title": "PNY RTX 5070", "source": "Best Buy", "price": "$579", "product_id": "p2"},
        ]
        clusters = consolidate_offers(offers)
        self.assertEqual(len(clusters), 2)


if __name__ == "__main__":
    unittest.main()
