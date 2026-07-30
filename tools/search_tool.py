from __future__ import annotations

from typing import Any, Dict, List

from search_api import google_shopping_search


class SearchTool:
    @staticmethod
    def search(query: str) -> Dict[str, Any]:
        return google_shopping_search(query)

    @staticmethod
    def extract_shopping_results(response: Dict[str, Any]) -> List[Dict[str, Any]]:
        return response.get("shopping_results", [])
