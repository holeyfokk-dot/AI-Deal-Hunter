from dataclasses import dataclass

@dataclass
class Product:
    title: str
    price: float
    store: str
    url: str