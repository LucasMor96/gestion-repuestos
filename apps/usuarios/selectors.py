from django.db.models import Sum

from .models import Proveedor, Tecnico


def contexto_moderacion():
    return {
        'tecnicos_pendientes': Tecnico.objects.filter(estado='pendiente').select_related('usuario'),
        'proveedores_pendientes': Proveedor.objects.filter(estado='pendiente').select_related('usuario'),
        'tecnicos_activos': Tecnico.objects.filter(estado='aprobado').select_related('usuario'),
        'proveedores_activos': Proveedor.objects.filter(estado='aprobado').select_related('usuario'),
        'tecnicos_inactivos': Tecnico.objects.filter(estado__in=['rechazado', 'suspendido']).select_related('usuario'),
        'proveedores_inactivos': Proveedor.objects.filter(estado__in=['rechazado', 'suspendido']).select_related('usuario'),
    }


def articulos_vendidos_proveedor(proveedor):
    return proveedor.pedidos_recibidos.filter(estado='completado').aggregate(
        total=Sum('cantidad')
    )['total'] or 0
