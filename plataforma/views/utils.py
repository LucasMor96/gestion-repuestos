from math import atan2, cos, radians, sin, sqrt

from django.contrib import messages


def solo_staff(request):
    if not request.user.is_staff:
        messages.error(request, 'No tenés permisos para acceder a esta sección.')
        return False
    return True


def get_proveedor_o_403(request):
    """Devuelve el perfil Proveedor del usuario o None si no corresponde."""
    if not hasattr(request.user, 'proveedor'):
        messages.error(request, 'Esta sección es solo para proveedores.')
        return None
    return request.user.proveedor


def get_tecnico_o_403(request):
    """Devuelve el perfil Tecnico del usuario o None si no corresponde."""
    if not hasattr(request.user, 'tecnico'):
        messages.error(request, 'Esta sección es solo para técnicos.')
        return None
    return request.user.tecnico


def haversine(lat1, lon1, lat2, lon2):
    """Distancia en km entre dos coordenadas."""
    radius_km = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return radius_km * 2 * atan2(sqrt(a), sqrt(1 - a))
