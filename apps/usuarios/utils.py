from django.contrib import messages


def normalizar_email(email):
    """El identificador de acceso no distingue mayusculas ni espacios externos."""
    return email.strip().lower()


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
