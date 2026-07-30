from __future__ import annotations

from typing import Any, Dict, Optional


class PartsTool:
    def find_compatible_parts(self, vin: str, part_number: str) -> Dict[str, Any]:
        return {
            "vin": vin,
            "part_number": part_number,
            "compatible": None,
            "notes": "Parts lookup is not yet implemented.",
        }

    def list_recommended_parts(self, vin: str) -> Dict[str, Optional[str]]:
        return {
            "vin": vin,
            "recommended_parts": [],
            "notes": "Placeholder implementation.",
        }
