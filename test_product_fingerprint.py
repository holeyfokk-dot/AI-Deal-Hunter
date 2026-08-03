import unittest

from tools.product_fingerprint import (
    extract_identifiers,
    extract_mpn_from_title,
    model_text_key,
    product_fingerprint,
)


class TestMPNExtraction(unittest.TestCase):
    def test_extracts_real_part_numbers(self):
        self.assertEqual(
            extract_mpn_from_title("Sony PlayStation 5 Pro Console CFI-7119"), "CFI-7119"
        )
        self.assertEqual(
            extract_mpn_from_title("AMD Ryzen 7 7800X3D 100-100000910WOF"),
            "100-100000910WOF",
        )
        self.assertEqual(
            extract_mpn_from_title("ASUS TUF-RTX5070-O12G-GAMING Graphics Card"),
            "TUF-RTX5070-O12G-GAMING",
        )

    def test_ignores_specs_and_plain_titles(self):
        # RAM speed / core-count specs must not be treated as part numbers.
        self.assertIsNone(extract_mpn_from_title("AMD Ryzen 7 7800X3D DDR5-6000 8-Core"))
        self.assertIsNone(extract_mpn_from_title("ASUS TUF GeForce RTX 5070 OC Edition"))
        self.assertIsNone(extract_mpn_from_title("Pokemon Legends Z-a Bundle"))


class TestIdentifierExtraction(unittest.TestCase):
    def test_explicit_fields(self):
        ids = extract_identifiers({"title": "x", "gtin": "0197105512345", "upc": "197105512345"})
        self.assertEqual(ids["gtin"], "0197105512345")
        self.assertEqual(ids["upc"], "197105512345")

    def test_nested_specs_field(self):
        ids = extract_identifiers({"title": "x", "specs": {"mpn": "90YV0M80-M0AA00"}})
        self.assertEqual(ids["mpn"], "90YV0M80-M0AA00")


class TestFingerprintPriority(unittest.TestCase):
    def test_gtin_beats_everything(self):
        item = {"title": "ASUS RTX 5070 CFI-7119", "gtin": "0197105512345", "product_id": "999"}
        self.assertEqual(product_fingerprint(item), "gtin:0197105512345")

    def test_mpn_from_title_beats_product_id(self):
        # Same product from two retailers with different Google product_ids but
        # the same manufacturer part number must collapse to one fingerprint.
        a = {"title": "Sony PS5 Pro CFI-7119", "source": "Amazon", "product_id": "111"}
        b = {"title": "PlayStation 5 Pro Console CFI-7119", "source": "Best Buy", "product_id": "222"}
        self.assertEqual(product_fingerprint(a), product_fingerprint(b))
        self.assertEqual(product_fingerprint(a), "mpn:CFI-7119")

    def test_different_mpn_does_not_collapse(self):
        a = {"title": "Sony PS5 Pro CFI-7119"}
        b = {"title": "Sony PS5 Pro CFI-7019"}
        self.assertNotEqual(product_fingerprint(a), product_fingerprint(b))

    def test_falls_back_to_product_id_then_model(self):
        self.assertEqual(product_fingerprint({"title": "ASUS RTX 5070", "product_id": "42"}), "pid:42")
        self.assertTrue(product_fingerprint({"title": "ASUS RTX 5070"}).startswith("model:"))
        self.assertEqual(
            model_text_key("ASUS TUF RTX 5070 OC"), model_text_key("ASUS TUF GeForce RTX 5070")
        )


if __name__ == "__main__":
    unittest.main()
