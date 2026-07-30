import unittest
from datetime import datetime, timezone
from typing import Any, Dict, List

from agents.lightning_mcqueen import LightningMcQueen
from models.vehicle_result import VehicleResult


class DummyVisorProvider:
    def search(self, query: str) -> Dict[str, Any]:
        return {
            "status": "ok",
            "listings": [
                {
                    "id": "VIN123",
                    "year": 2018,
                    "make": "Toyota",
                    "model": "Camry",
                    "trim": "SE",
                    "price": 17999.0,
                    "market_value": 18999.0,
                    "mileage": 42000,
                    "dealer_name": "AutoHouse",
                    "dealer_type": "Independent",
                    "location": "Denver, CO",
                    "condition": "Used",
                    "title_status": "Clean",
                    "accident_count": 0,
                    "one_owner": True,
                    "service_history_available": True,
                    "engine": "2.5L I4",
                    "transmission": "Automatic",
                    "drivetrain": "FWD",
                    "exterior_color": "Blue",
                    "interior_color": "Gray",
                    "listing_url": "https://example.com/listing/vin123",
                    "options": ["Bluetooth", "Backup Camera"],
                }
            ],
        }

    def normalize(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "vehicle_id": raw_result["id"],
            "year": raw_result["year"],
            "make": raw_result["make"],
            "model": raw_result["model"],
            "trim": raw_result["trim"],
            "price": raw_result["price"],
            "market_value": raw_result["market_value"],
            "mileage": raw_result["mileage"],
            "dealer_name": raw_result["dealer_name"],
            "dealer_type": raw_result["dealer_type"],
            "location": raw_result["location"],
            "condition": raw_result["condition"],
            "title_status": raw_result["title_status"],
            "accident_count": raw_result["accident_count"],
            "one_owner": raw_result["one_owner"],
            "service_history_available": raw_result["service_history_available"],
            "engine": raw_result["engine"],
            "transmission": raw_result["transmission"],
            "drivetrain": raw_result["drivetrain"],
            "exterior_color": raw_result["exterior_color"],
            "interior_color": raw_result["interior_color"],
            "listing_url": raw_result["listing_url"],
            "source": "TestVisor",
            "options": raw_result["options"],
        }

    def is_available(self, response: Dict[str, Any]) -> bool:
        return response.get("status") == "ok"

    def get_error(self, response: Dict[str, Any]) -> str:
        return ""


class TestLightningMcQueen(unittest.TestCase):
    def test_handle_returns_vehicle_results(self):
        from tools.vehicle_search_tool import VehicleSearchTool

        dummy_provider = DummyVisorProvider()
        search_tool = VehicleSearchTool(dummy_provider)
        specialist = LightningMcQueen(search_tool=search_tool)

        response = specialist.handle({"query": "Toyota Camry"})

        self.assertEqual(response["status"], "ok")
        self.assertIn("vehicles", response)
        self.assertIsInstance(response["vehicles"], list)

        self.assertGreaterEqual(len(response["vehicles"]), 1)
        vehicle = response["vehicles"][0]
        self.assertIsInstance(vehicle, VehicleResult)
        self.assertEqual(vehicle.vehicle_id, "VIN123")
        self.assertEqual(vehicle.make, "Toyota")
        self.assertTrue(0 <= vehicle.confidence_score <= 100)
        self.assertTrue(0 <= vehicle.recommendation_score <= 100)

    def test_handle_reports_invalid_query(self):
        specialist = LightningMcQueen()
        response = specialist.handle({"query": None})

        self.assertEqual(response["status"], "invalid_query")
        self.assertEqual(response["vehicles"], [])

    def test_handle_reports_unavailable_provider(self):
        class UnavailableProvider(DummyVisorProvider):
            def search(self, query: str) -> Dict[str, Any]:
                return {"status": "error", "error": "service down"}

        from tools.vehicle_search_tool import VehicleSearchTool

        provider = UnavailableProvider()
        search_tool = VehicleSearchTool(provider)
        specialist = LightningMcQueen(search_tool=search_tool)

        response = specialist.handle({"query": "Toyota Camry"})

        self.assertEqual(response["status"], "visor_unavailable")
        self.assertEqual(response["vehicles"], [])
        self.assertEqual(response["error"], "service down")

    def test_vehicle_result_to_dict(self):
        vehicle = VehicleResult(
            id="VIN123",
            specialist="Lightning McQueen",
            timestamp=datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc),
            confidence_score=87.5,
            metadata={"source": "TestVisor"},
            vehicle_id="VIN123",
            year=2018,
            make="Toyota",
            model="Camry",
            trim="SE",
            price=17999.0,
            market_value=18999.0,
            mileage=42000.0,
            dealer_name="AutoHouse",
            dealer_type="Independent",
            location="Denver, CO",
            condition="Used",
            title_status="Clean",
            accident_count=0,
            one_owner=True,
            service_history_available=True,
            engine="2.5L I4",
            transmission="Automatic",
            drivetrain="FWD",
            exterior_color="Blue",
            interior_color="Gray",
            recommendation_score=92.2,
            listing_url="https://example.com/listing/vin123",
            source="TestVisor",
            options=["Bluetooth", "Backup Camera"],
        )

        serialized = vehicle.to_dict()
        self.assertEqual(serialized["vehicle_id"], "VIN123")
        self.assertEqual(serialized["source"], "TestVisor")
        self.assertEqual(serialized["confidence_score"], 87.5)
        self.assertEqual(serialized["recommendation_score"], 92.2)


if __name__ == "__main__":
    unittest.main()
