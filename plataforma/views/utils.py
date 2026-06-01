from math import atan2, cos, radians, sin, sqrt

from django.contrib import messages


def solo_staff(request):
    if not request.user.is_active or not request.user.is_staff:
        messages.error(request, 'No tenes permisos para acceder a esta seccion.')
        return False
    return True


def perfil_aprobado(perfil):
    return (
        perfil.usuario.is_active
        and perfil.estado == 'aprobado'
        and perfil.is_approved
    )


def get_proveedor_o_403(request):
    """Devuelve el perfil Proveedor del usuario o None si no corresponde."""
    if not hasattr(request.user, 'proveedor'):
        messages.error(request, 'Esta seccion es solo para proveedores.')
        return None

    proveedor = request.user.proveedor
    if not perfil_aprobado(proveedor):
        messages.error(request, 'Tu cuenta de proveedor todavia no esta habilitada.')
        return None

    return proveedor


def get_tecnico_o_403(request):
    """Devuelve el perfil Tecnico del usuario o None si no corresponde."""
    if not hasattr(request.user, 'tecnico'):
        messages.error(request, 'Esta seccion es solo para tecnicos.')
        return None

    tecnico = request.user.tecnico
    if not perfil_aprobado(tecnico):
        messages.error(request, 'Tu cuenta de tecnico todavia no esta habilitada.')
        return None

    return tecnico


def haversine(lat1, lon1, lat2, lon2):
    """Distancia en km entre dos coordenadas."""
    radius_km = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return radius_km * 2 * atan2(sqrt(a), sqrt(1 - a))
