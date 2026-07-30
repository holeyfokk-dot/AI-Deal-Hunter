from __future__ import annotations

from typing import Any, Dict, Optional


class ValuationTool:
    def estimate_market_value(
        self,
        year: int,
        make: str,
        model: str,
        mileage: float,
    ) -> Dict[str, Optional[Any]]:
        return {
            "year": year,
            "make": make,
            "model": model,
            "mileage": mileage,
            "estimated_value": None,
            "confidence": 0.0,
            "notes": "Valuation is not yet implemented.",
        }
