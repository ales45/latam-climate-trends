from typing import NamedTuple


class City(NamedTuple):
    name: str
    country: str
    latitude: float
    longitude: float


CITIES = [
    City("Mexico City", "Mexico", 19.43, -99.13),
    City("Bogota", "Colombia", 4.71, -74.07),
    City("Quito", "Ecuador", -0.18, -78.47),
    City("Lima", "Peru", -12.05, -77.04),
    City("Santiago", "Chile", -33.45, -70.67),
    City("Buenos Aires", "Argentina", -34.60, -58.38),
]
