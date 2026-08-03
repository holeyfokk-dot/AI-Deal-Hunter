import unittest

from tools.product_page_verify import (
    MISMATCH,
    OUT_OF_STOCK,
    UNVERIFIED,
    VERIFIED,
    extract_product_signals,
    verify_from_html,
)
from tools.retailer_trust import trust_stars

JSONLD_INSTOCK = """<html><head><title>Buy ASUS RTX 5070 | Store</title>
<script type="application/ld+json">
{"@type":"Product","name":"ASUS TUF Gaming GeForce RTX 5070 OC",
 "brand":{"@type":"Brand","name":"ASUS"},"sku":"90YV0M80-M0AA00",
 "gtin13":"0197105512345","mpn":"TUF-RTX5070-O12G",
 "offers":{"@type":"Offer","price":"599.99","availability":"https://schema.org/InStock"}}
</script></head><body></body></html>"""

JSONLD_WRONG_MODEL = """<html><head><title>Graphics Card</title>
<script type="application/ld+json">
{"@type":"Product","name":"GeForce RTX 4070 Super 12GB",
 "offers":{"availability":"https://schema.org/InStock"}}
</script></head></html>"""

JSONLD_OUT_OF_STOCK = """<html><head>
<script type="application/ld+json">
{"@type":"Product","name":"ASUS RTX 5070 OC",
 "offers":{"availability":"https://schema.org/OutOfStock"}}
</script></head></html>"""

OG_ONLY = '<html><head><meta property="og:title" content="Sony PlayStation 5 Console"></head></html>'
TITLE_ONLY = "<html><head><title>PlayStation 5 Slim Digital Edition</title></head></html>"
NO_SIGNALS = "<html><body>welcome to our store</body></html>"


class TestSignalExtraction(unittest.TestCase):
    def test_extracts_jsonld_identifiers(self):
        sig = extract_product_signals(JSONLD_INSTOCK)
        self.assertEqual(sig["title"], "ASUS TUF Gaming GeForce RTX 5070 OC")
        self.assertEqual(sig["identifiers"]["gtin"], "0197105512345")
        self.assertEqual(sig["identifiers"]["mpn"], "TUF-RTX5070-O12G")
        self.assertEqual(sig["identifiers"]["sku"], "90YV0M80-M0AA00")
        self.assertEqual(sig["identifiers"]["brand"], "ASUS")

    def test_falls_back_to_og_then_title(self):
        self.assertEqual(extract_product_signals(OG_ONLY)["title"], "Sony PlayStation 5 Console")
        self.assertEqual(
            extract_product_signals(TITLE_ONLY)["title"], "PlayStation 5 Slim Digital Edition"
        )


class TestVerifyFromHTML(unittest.TestCase):
    def test_verified_when_page_matches_query(self):
        r = verify_from_html(JSONLD_INSTOCK, "RTX 5070")
        self.assertEqual(r.status, VERIFIED)
        self.assertIn("gtin", r.identifiers)

    def test_mismatch_rejects_wrong_model(self):
        r = verify_from_html(JSONLD_WRONG_MODEL, "RTX 5070")
        self.assertEqual(r.status, MISMATCH)
        self.assertTrue(r.is_mismatch)

    def test_mismatch_rejects_wrong_variant(self):
        # PS5 Pro search, but the page is a PS5 Slim.
        self.assertEqual(verify_from_html(TITLE_ONLY, "PS5 Pro").status, MISMATCH)

    def test_og_title_match(self):
        self.assertEqual(verify_from_html(OG_ONLY, "PlayStation 5").status, VERIFIED)

    def test_out_of_stock_flagged_unless_requested(self):
        self.assertEqual(verify_from_html(JSONLD_OUT_OF_STOCK, "RTX 5070").status, OUT_OF_STOCK)
        self.assertEqual(
            verify_from_html(JSONLD_OUT_OF_STOCK, "RTX 5070", want_out_of_stock=True).status,
            VERIFIED,
        )

    def test_unverified_when_no_signals(self):
        self.assertEqual(verify_from_html(NO_SIGNALS, "RTX 5070").status, UNVERIFIED)


class TestTrustStars(unittest.TestCase):
    def test_star_ratings(self):
        self.assertEqual(trust_stars("Best Buy", "verified"), "★★★★★ Verified")
        self.assertEqual(trust_stars("Best Buy"), "★★★★☆ Known retailer")
        self.assertEqual(trust_stars("eBay"), "★★★☆☆ Limited history")
        self.assertEqual(trust_stars("NeverSeenStore"), "★★☆☆☆ Unknown")
        self.assertEqual(trust_stars("Best Buy", "mismatch"), "★☆☆☆☆ High Risk")


if __name__ == "__main__":
    unittest.main()
