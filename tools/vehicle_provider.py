from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class VehicleProvider(ABC):
    @abstractmethod
    def search(self, query: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def source_name(self) -> str:
        raise NotImplementedError
