from __future__ import annotations

from typing import Any, Dict, List

from .vehicle_provider import VehicleProvider


class VehicleSearchTool:
    def __init__(self, provider: VehicleProvider) -> None:
        self.provider = provider

    def search(self, query: str) -> Dict[str, Any]:
        return self.provider.search(query)

    def normalize_listings(self, raw_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        listings = raw_response.get("listings", [])
        return [self.provider.normalize(listing) for listing in listings]

    def is_available(self, raw_response: Dict[str, Any]) -> bool:
        return self.provider.is_available(raw_response)

    def get_error(self, raw_response: Dict[str, Any]) -> str:
        provider_error = self.provider.get_error(raw_response)
        if provider_error:
            return provider_error

        return raw_response.get("error", "unknown error")
