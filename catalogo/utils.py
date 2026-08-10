from math import atan2, cos, radians, sin, sqrt


def haversine(lat1, lon1, lat2, lon2):
    """Distancia en km entre dos coordenadas."""
    radius_km = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return radius_km * 2 * atan2(sqrt(a), sqrt(1 - a))
