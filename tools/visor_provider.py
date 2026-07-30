from __future__ import annotations

from typing import Any, Dict, Optional

from .vehicle_provider import VehicleProvider


class VisorProvider(VehicleProvider):
    STATUS_OK = "ok"

    def search(self, query: str) -> Dict[str, Any]:
        # Placeholder for Visor.vin search integration.
        return {
            "status": self.STATUS_OK,
            "listings": [],
            "source": "Visor.vin",
        }

    def normalize(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "vehicle_id": raw_result.get("id", ""),
            "year": raw_result.get("year"),
            "make": raw_result.get("make"),
            "model": raw_result.get("model"),
            "trim": raw_result.get("trim"),
            "price": self._parse_float(raw_result.get("price"), 0.0),
            "market_value": self._parse_float(raw_result.get("market_value")),
            "mileage": self._parse_float(raw_result.get("mileage"), 0.0),
            "dealer_name": raw_result.get("dealer_name"),
            "dealer_type": raw_result.get("dealer_type"),
            "location": raw_result.get("location"),
            "condition": raw_result.get("condition"),
            "title_status": raw_result.get("title_status"),
            "accident_count": self._parse_int(raw_result.get("accident_count")),
            "one_owner": raw_result.get("one_owner"),
            "service_history_available": raw_result.get("service_history_available"),
            "engine": raw_result.get("engine"),
            "transmission": raw_result.get("transmission"),
            "drivetrain": raw_result.get("drivetrain"),
            "exterior_color": raw_result.get("exterior_color"),
            "interior_color": raw_result.get("interior_color"),
            "listing_url": raw_result.get("listing_url", ""),
            "source": self.source_name(),
            "options": raw_result.get("options", []),
        }

    def source_name(self) -> str:
        return "Visor.vin"

    def is_available(self, response: Dict[str, Any]) -> bool:
        return response.get("status") == self.STATUS_OK

    def get_error(self, response: Dict[str, Any]) -> Optional[str]:
        if not self.is_available(response):
            return response.get("error", "visor unavailable")
        return None

    def _parse_float(self, value: Any, default: Optional[float] = None) -> Optional[float]:
        if value is None:
            return default

        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _parse_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None

        try:
            return int(value)
        except (ValueError, TypeError):
            return None
