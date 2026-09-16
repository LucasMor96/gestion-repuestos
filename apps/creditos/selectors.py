from django.db.models import Prefetch, Q

from apps.pedidos.models import Pedido
from apps.usuarios.models import Tecnico

from .models import Credito, PagoCredito


def creditos_activos_tecnico(tecnico):
    return Credito.objects.para_tecnico(tecnico).activos().prefetch_related(
        Prefetch('pagos', queryset=PagoCredito.objects.filter(estado='pendiente'), to_attr='pagos_pendientes')
    )


def creditos_activos_proveedor(proveedor):
    return Credito.objects.para_proveedor(proveedor).activos().order_by(
        'tecnico__usuario__last_name'
    )


def deudas_proveedor(proveedor):
    return Credito.objects.para_proveedor(proveedor).con_deuda()


def buscar_tecnicos_aprobados(busqueda):
    if not busqueda:
        return Tecnico.objects.none()
    try:
        return Tecnico.objects.filter(pk=int(busqueda), is_approved=True).select_related('usuario')
    except ValueError:
        return Tecnico.objects.filter(
            Q(usuario__first_name__icontains=busqueda)
            | Q(usuario__last_name__icontains=busqueda),
            is_approved=True,
        ).select_related('usuario')


def pedidos_de_credito(*, proveedor, tecnico):
    return Pedido.objects.deuda_credito(proveedor=proveedor, tecnico=tecnico)


def pagos_pendientes_proveedor(proveedor):
    return PagoCredito.objects.filter(
        credito__proveedor=proveedor, estado='pendiente'
    ).select_related('credito__tecnico__usuario', 'credito__proveedor')
