from serpapi import GoogleSearch
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("SERPAPI_KEY")


def google_shopping_search(query):

    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": API_KEY,
        "gl": "us",
        "hl": "en"
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    return results