from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents.base_agent import AgentMetadata, BaseAgent
from models.result_status import ResultStatus
from models.vehicle_result import VehicleResult
from tools.vehicle_search_tool import VehicleSearchTool
from tools.vin_tool import VINTool
from tools.visor_provider import VisorProvider


class LightningMcQueen(BaseAgent):
    @classmethod
    def create_metadata(cls) -> AgentMetadata:
        return AgentMetadata(
            name="Lightning McQueen",
            version="1.0.0",
            author="AI Deal Hunter",
            description="Automotive Specialist",
            capabilities=[
                "vehicle_search",
                "vin_analysis",
                "vehicle_compare",
                "listing_analysis",
                "vehicle_recommendation",
            ],
            priority=20,
            enabled=True,
            required_tools=["VehicleSearchTool", "VINTool"],
        )

    def __init__(
        self,
        search_tool: Optional[VehicleSearchTool] = None,
        vin_tool: Optional[VINTool] = None,
    ) -> None:
        super().__init__()
        self.search_tool = search_tool or VehicleSearchTool(VisorProvider())
        self.vin_tool = vin_tool or VINTool()

    def can_handle(self, capability: str) -> bool:
        return capability in self.metadata.capabilities

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        vin = request.get("vin")
        query = request.get("query", "")

        if vin:
            return self._handle_vin_analysis(vin)

        if not query or not isinstance(query, str):
            return {
                "status": ResultStatus.INVALID_REQUEST,
                "vehicles": [],
            }

        raw_response = self.search_tool.search(query)

        if not self.search_tool.is_available(raw_response):
            return {
                "status": ResultStatus.PROVIDER_UNAVAILABLE,
                "error": self.search_tool.get_error(raw_response),
                "vehicles": [],
            }

        normalized_listings = self.search_tool.normalize_listings(raw_response)
        vehicle_results = self._build_vehicle_results(normalized_listings)
        status = ResultStatus.SUCCESS if vehicle_results else ResultStatus.NO_RESULTS

        return {
            "status": status,
            "vehicles": vehicle_results,
        }

    def _handle_vin_analysis(self, vin: Any) -> Dict[str, Any]:
        if not isinstance(vin, str) or not self.vin_tool.validate(vin):
            return {
                "status": ResultStatus.INVALID_REQUEST,
                "vin": vin,
                "result": None,
            }

        vin_result = self.vin_tool.build_result(vin, self.metadata.name, confidence_score=90.0)
        if vin_result is None:
            return {
                "status": ResultStatus.ERROR,
                "vin": vin,
                "result": None,
            }

        return {
            "status": ResultStatus.SUCCESS,
            "vin": vin,
            "result": vin_result,
        }

    def _build_vehicle_results(self, listings: List[Dict[str, Any]]) -> List[VehicleResult]:
        results: List[VehicleResult] = []

        for listing in listings:
            result = VehicleResult(
                id=str(listing.get("vehicle_id", "")),
                specialist=self.metadata.name,
                timestamp=datetime.now(timezone.utc),
                confidence_score=self._calculate_confidence(listing),
                metadata={"source": listing.get("source")},
                vehicle_id=str(listing.get("vehicle_id", "")),
                year=listing.get("year"),
                make=listing.get("make"),
                model=listing.get("model"),
                trim=listing.get("trim"),
                price=listing.get("price", 0.0),
                market_value=listing.get("market_value"),
                mileage=listing.get("mileage", 0.0),
                dealer_name=listing.get("dealer_name"),
                dealer_type=listing.get("dealer_type"),
                location=listing.get("location"),
                condition=listing.get("condition"),
                title_status=listing.get("title_status"),
                accident_count=listing.get("accident_count"),
                one_owner=listing.get("one_owner"),
                service_history_available=listing.get("service_history_available"),
                engine=listing.get("engine"),
                transmission=listing.get("transmission"),
                drivetrain=listing.get("drivetrain"),
                exterior_color=listing.get("exterior_color"),
                interior_color=listing.get("interior_color"),
                recommendation_score=self._calculate_recommendation(listing),
                listing_url=listing.get("listing_url", ""),
                source=listing.get("source"),
                options=listing.get("options", []),
            )
            results.append(result)

        return results

    def _calculate_confidence(self, listing: Dict[str, Any]) -> float:
        year = listing.get("year") or 0
        price = listing.get("price") or 0.0
        mileage = listing.get("mileage") or 0.0

        score = 50.0
        if year and year >= 2015:
            score += 10.0
        if price and price > 0:
            score += min(20.0, max(0.0, 20.0 - (price / 10000)))
        if mileage and mileage < 100000:
            score += 10.0

        return min(100.0, max(0.0, round(score, 2)))

    def _calculate_recommendation(self, listing: Dict[str, Any]) -> float:
        confidence = self._calculate_confidence(listing)
        value_delta = 0.0
        if listing.get("market_value") and listing.get("price"):
            value_delta = (listing.get("market_value") - listing.get("price")) / max(listing.get("market_value"), 1)

        score = confidence + min(20.0, max(-20.0, value_delta * 50))
        return min(100.0, max(0.0, round(score, 2)))
