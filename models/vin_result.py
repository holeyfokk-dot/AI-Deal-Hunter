from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from .base_result import BaseResult


@dataclass
class VINResult(BaseResult):
    vin: str
    year: Optional[int]
    make: Optional[str]
    model: Optional[str]
    trim: Optional[str]
    engine: Optional[str]
    transmission: Optional[str]
    drivetrain: Optional[str]
    body_style: Optional[str]
    manufacturer: Optional[str]

    def __post_init__(self) -> None:
        if len(self.vin) != 17:
            raise ValueError("vin must be 17 characters")

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "vin": self.vin,
            "year": self.year,
            "make": self.make,
            "model": self.model,
            "trim": self.trim,
            "engine": self.engine,
            "transmission": self.transmission,
            "drivetrain": self.drivetrain,
            "body_style": self.body_style,
            "manufacturer": self.manufacturer,
        })
        return base
