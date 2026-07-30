from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .base_result import BaseResult


@dataclass
class DealResult(BaseResult):
    product_name: str
    current_price: float
    historical_lowest_price: Optional[float]
    discount_percent: Optional[float]
    store: str
    store_reputation: str
    platform: Optional[str]
    drm: Optional[str]
    region_lock: Optional[str]
    bundle_included: bool
    url: str
    deal_score: float

    def to_dict(self) -> dict[str, object]:
        base = super().to_dict()
        base.update({
            "product_name": self.product_name,
            "current_price": self.current_price,
            "historical_lowest_price": self.historical_lowest_price,
            "discount_percent": self.discount_percent,
            "store": self.store,
            "store_reputation": self.store_reputation,
            "platform": self.platform,
            "drm": self.drm,
            "region_lock": self.region_lock,
            "bundle_included": self.bundle_included,
            "url": self.url,
            "deal_score": self.deal_score,
        })
        return base
