import json

def load_watchlist():
    with open("watchlist.json", "r") as file:
        return json.load(file)