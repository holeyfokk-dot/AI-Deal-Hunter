import unittest

from models.result_status import ResultStatus
from tools.vin_tool import VINTool


class TestVINTool(unittest.TestCase):
    def test_validate_accepts_valid_vin(self):
        self.assertTrue(VINTool.validate("1HGCM82633A004352"))

    def test_validate_rejects_invalid_vin(self):
        self.assertFalse(VINTool.validate("INVALIDVIN1234567"))

    def test_decode_returns_expected_keys(self):
        decoded = VINTool.decode("1HGCM82633A004352")
        self.assertIsNotNone(decoded)
        self.assertIn("vin", decoded)
        self.assertIn("year", decoded)
        self.assertIn("make", decoded)
        self.assertIn("model", decoded)
        self.assertIn("engine", decoded)

    def test_build_result_returns_vin_result(self):
        result = VINTool.build_result("1HGCM82633A004352", "Lightning McQueen", 85.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.vin, "1HGCM82633A004352")
        self.assertEqual(result.specialist, "Lightning McQueen")
        self.assertEqual(result.confidence_score, 85.0)

    def test_build_result_returns_none_for_invalid_vin(self):
        result = VINTool.build_result("BADVIN123", "Lightning McQueen", 85.0)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
