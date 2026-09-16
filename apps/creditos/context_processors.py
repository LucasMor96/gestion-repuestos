from .models import PagoCredito


def pagos_credito_pendientes(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'proveedor'):
        return {'pagos_credito_pendientes_count': 0}
    return {'pagos_credito_pendientes_count': PagoCredito.objects.filter(
        credito__proveedor=request.user.proveedor, estado='pendiente'
    ).count()}
