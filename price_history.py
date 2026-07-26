import json
import os

FILE = "prices.json"


def load_prices():
    if not os.path.exists(FILE):
        return {}

    with open(FILE, "r") as f:
        return json.load(f)


def save_prices(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)


def has_price_changed(product, price):
    prices = load_prices()

    old_price = prices.get(product)

    if old_price == price:
        return False

    prices[product] = price
    save_prices(prices)

    return True


def previous_price(product):
    prices = load_prices()
    return prices.get(product)
