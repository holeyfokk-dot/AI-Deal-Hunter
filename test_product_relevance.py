import unittest

from tools.product_relevance import (
    ProductType,
    classify_product_type,
    classify_query_type,
    group_results,
    is_bundle,
    is_prebuilt_pc,
    is_relevant,
    same_primary_product,
    semantic_similarity,
)


def _items(*titles):
    return [{"title": t, "price": "$100"} for t in titles]


class TestClassification(unittest.TestCase):
    def test_product_types(self):
        self.assertEqual(classify_product_type("AMD Ryzen 7 7800X3D 8-Core Processor"), ProductType.CPU)
        self.assertEqual(classify_product_type("ASUS GeForce RTX 5070 Graphics Card"), ProductType.GPU)
        self.assertEqual(classify_product_type("PlayStation 5 Console"), ProductType.CONSOLE)
        self.assertEqual(classify_product_type("PS5 DualSense Wireless Controller"), ProductType.ACCESSORY)

    def test_prebuilt_pc_detection(self):
        self.assertTrue(is_prebuilt_pc("Hoengager Gaming PC - Ryzen 7 7800X3D - RTX 5050 - 1TB SSD - 16GB DDR5"))
        self.assertTrue(is_prebuilt_pc("AMD Ryzen 7 7800X3D + RTX 5070 Desktop Computer"))
        self.assertFalse(is_prebuilt_pc("AMD Ryzen 7 7800X3D 8-Core Processor"))
        self.assertFalse(is_prebuilt_pc("ASUS GeForce RTX 5070 OC 12GB GDDR7"))
        self.assertEqual(
            classify_product_type("Hoengager Gaming PC - Ryzen 7 7800X3D - RTX 5050 - 1TB SSD - 16GB DDR5"),
            ProductType.PREBUILT_PC,
        )

    def test_bundle_detection(self):
        self.assertTrue(is_bundle("Nintendo Switch 2 + Mario Kart Bundle"))
        self.assertTrue(is_bundle("Ryzen 7 7800X3D CPU + Motherboard Combo"))
        self.assertFalse(is_bundle("PlayStation 5 Console"))

    def test_query_types(self):
        self.assertEqual(classify_query_type("RTX 5070"), ProductType.GPU)
        self.assertEqual(classify_query_type("Ryzen 7 7800X3D"), ProductType.CPU)
        self.assertEqual(classify_query_type("PlayStation 5"), ProductType.CONSOLE)


class TestSemanticSimilarity(unittest.TestCase):
    def test_same_product_more_similar_than_different(self):
        s_same = semantic_similarity("PlayStation 5", "Sony PlayStation 5 Console")
        s_diff = semantic_similarity("PlayStation 5", "Xbox Series X Console")
        self.assertGreater(s_same, s_diff)

    def test_model_and_variant_matching(self):
        self.assertTrue(same_primary_product("RTX 5070", "ASUS TUF GeForce RTX 5070 OC"))
        self.assertFalse(same_primary_product("RTX 5070", "GeForce RTX 5090"))
        self.assertFalse(same_primary_product("RTX 5070", "GeForce RTX 5070 Ti"))
        self.assertFalse(same_primary_product("PlayStation 5", "PlayStation 5 Pro"))
        self.assertFalse(same_primary_product("Nintendo Switch 2", "Nintendo Switch"))


class TestRelevanceRejections(unittest.TestCase):
    def test_cpu_query_rejects_full_pc(self):
        ok, reason = is_relevant("Ryzen 7 7800X3D", {"title": "Gaming PC Ryzen 7 7800X3D RTX 5070 1TB SSD 16GB DDR5"})
        self.assertFalse(ok)
        self.assertIn("full pc", reason.lower())

    def test_gpu_query_rejects_full_pc(self):
        ok, _ = is_relevant("RTX 5070", {"title": "Prebuilt Gaming Desktop RTX 5070 Ryzen 5"})
        self.assertFalse(ok)

    def test_console_query_rejects_controller(self):
        ok, reason = is_relevant("PlayStation 5", {"title": "PS5 DualSense Wireless Controller"})
        self.assertFalse(ok)
        self.assertIn("accessory", reason.lower())

    def test_cpu_query_rejects_gpu(self):
        ok, _ = is_relevant("Ryzen 7 7800X3D", {"title": "GeForce RTX 5070 Graphics Card"})
        self.assertFalse(ok)

    def test_accepts_matching_product(self):
        ok, _ = is_relevant("RTX 5070", {"title": "MSI GeForce RTX 5070 Gaming Trio OC"})
        self.assertTrue(ok)


class TestGroupingAndMarketAverage(unittest.TestCase):
    def test_groups_separate_bundles_and_reject_unrelated(self):
        items = _items(
            "AMD Ryzen 7 7800X3D 8-Core Processor",
            "AMD Ryzen 7 7800X3D Desktop Processor",
            "Ryzen 7 7800X3D CPU + Motherboard Combo",   # bundle
            "Hoengager Gaming PC Ryzen 7 7800X3D RTX 5070 1TB SSD 16GB DDR5",  # rejected
            "GeForce RTX 5070 Graphics Card",            # rejected (wrong type)
        )
        groups, rejected = group_results("Ryzen 7 7800X3D", items)
        self.assertIn("cpu", groups)
        self.assertIn("cpu_bundle", groups)
        self.assertEqual(len(groups["cpu"]), 2)
        self.assertEqual(len(groups["cpu_bundle"]), 1)
        self.assertEqual(len(rejected), 2)

    def test_market_average_excludes_prebuilt_pcs(self):
        # Without grouping, the $1500 PC would inflate the CPU market average.
        items = [
            {"title": "AMD Ryzen 7 7800X3D 8-Core Processor", "price": "$400"},
            {"title": "AMD Ryzen 7 7800X3D Desktop Processor", "price": "$420"},
            {"title": "Gaming PC Ryzen 7 7800X3D RTX 5070 1TB SSD 16GB DDR5", "price": "$1500"},
        ]
        groups, _ = group_results("Ryzen 7 7800X3D", items)
        cpu_prices = [it["price"] for it in groups["cpu"]]
        self.assertEqual(sorted(cpu_prices), ["$400", "$420"])
        self.assertNotIn("prebuilt_pc", groups)  # rejected for a CPU query


if __name__ == "__main__":
    unittest.main()
