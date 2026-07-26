from product import Product
from stores import Store


def search_products(search):

    products = [

        Product(
            title=f"{search} Found at Best Buy",
            price=549.99,
            store=Store.BEST_BUY,
            url="https://example.com/bestbuy"
        ),

        Product(
            title=f"{search} Found at Walmart",
            price=529.99,
            store=Store.WALMART,
            url="https://example.com/walmart"
        ),

        Product(
            title=f"{search} Found at Amazon",
            price=559.99,
            store=Store.AMAZON,
            url="https://example.com/amazon"
        )

    ]

    return products