from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class BaseResult:
    id: str
    specialist: str
    timestamp: datetime
    confidence_score: float
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict, kw_only=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "specialist": self.specialist,
            "timestamp": self.timestamp.isoformat(),
            "confidence_score": self.confidence_score,
            "metadata": self.metadata,
        }
