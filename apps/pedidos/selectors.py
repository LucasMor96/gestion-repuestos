from apps.usuarios.models import Proveedor

from .models import Pedido


def historial_tecnico(*, tecnico, fecha_desde='', fecha_hasta='', proveedor_id=''):
    return Pedido.objects.para_historial(
        tecnico=tecnico,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        proveedor_id=proveedor_id,
    )


def proveedores_del_historial(tecnico):
    return Proveedor.objects.filter(
        pedidos_recibidos__tecnico=tecnico
    ).distinct().order_by('nombre_negocio')


def pedidos_recibidos(proveedor):
    return Pedido.objects.recibidos_por(proveedor)
