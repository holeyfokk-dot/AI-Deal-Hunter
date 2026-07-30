from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_result import BaseResult


@dataclass
class VehicleResult(BaseResult):
    vehicle_id: str
    year: Optional[int]
    make: Optional[str]
    model: Optional[str]
    trim: Optional[str]
    price: float
    market_value: Optional[float]
    mileage: float
    dealer_name: Optional[str]
    dealer_type: Optional[str]
    location: Optional[str]
    condition: Optional[str]
    title_status: Optional[str]
    accident_count: Optional[int]
    one_owner: Optional[bool]
    service_history_available: Optional[bool]
    engine: Optional[str]
    transmission: Optional[str]
    drivetrain: Optional[str]
    exterior_color: Optional[str]
    interior_color: Optional[str]
    recommendation_score: float
    listing_url: str
    source: Optional[str]
    options: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.price < 0:
            raise ValueError("price must be >= 0")
        if self.mileage < 0:
            raise ValueError("mileage must be >= 0")
        if not 0 <= self.recommendation_score <= 100:
            raise ValueError("recommendation_score must be between 0 and 100")
        if not 0 <= self.confidence_score <= 100:
            raise ValueError("confidence_score must be between 0 and 100")
        if self.accident_count is not None and self.accident_count < 0:
            raise ValueError("accident_count must be >= 0")

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "vehicle_id": self.vehicle_id,
            "year": self.year,
            "make": self.make,
            "model": self.model,
            "trim": self.trim,
            "price": self.price,
            "market_value": self.market_value,
            "mileage": self.mileage,
            "dealer_name": self.dealer_name,
            "dealer_type": self.dealer_type,
            "location": self.location,
            "condition": self.condition,
            "title_status": self.title_status,
            "accident_count": self.accident_count,
            "one_owner": self.one_owner,
            "service_history_available": self.service_history_available,
            "engine": self.engine,
            "transmission": self.transmission,
            "drivetrain": self.drivetrain,
            "exterior_color": self.exterior_color,
            "interior_color": self.interior_color,
            "recommendation_score": self.recommendation_score,
            "listing_url": self.listing_url,
            "source": self.source,
            "options": self.options,
        })
        return base
