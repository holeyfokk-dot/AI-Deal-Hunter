from __future__ import annotations

from typing import Any, Dict, List, Optional


class VisorTool:
    VISOR_UNAVAILABLE = "visor_unavailable"

    @staticmethod
    def search(query: str) -> Dict[str, Any]:
        # Placeholder for Visor API integration.
        # This method should return a normalized response shape.
        return {
            "status": "ok",
            "listings": [],
        }

    @staticmethod
    def normalize_listing(raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": raw.get("id", ""),
            "year": raw.get("year"),
            "make": raw.get("make"),
            "model": raw.get("model"),
            "trim": raw.get("trim"),
            "price": raw.get("price", 0.0),
            "mileage": raw.get("mileage", 0.0),
            "dealer": raw.get("dealer"),
            "location": raw.get("location"),
            "title_status": raw.get("title_status"),
            "engine": raw.get("engine"),
            "transmission": raw.get("transmission"),
            "drivetrain": raw.get("drivetrain"),
            "exterior_color": raw.get("exterior_color"),
            "interior_color": raw.get("interior_color"),
            "listing_url": raw.get("listing_url", ""),
            "options": raw.get("options", []),
        }

    @staticmethod
    def is_available(response: Dict[str, Any]) -> bool:
        return response.get("status") == "ok"

    @staticmethod
    def get_error(response: Dict[str, Any]) -> Optional[str]:
        if response.get("status") != "ok":
            return response.get("error", "visor unavailable")
        return None
