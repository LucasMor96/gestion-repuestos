from django.db import IntegrityError, transaction

from apps.pedidos.models import Pedido

from .exceptions import ActorInvalido, CalificacionDuplicada, PedidoNoCompletado
from .models import CalificacionProveedor, CalificacionTecnico


def validar_calificacion_proveedor(*, pedido, tecnico):
    if pedido.tecnico_id != tecnico.pk:
        raise ActorInvalido('El pedido no pertenece al tecnico.')
    if pedido.estado != 'completado':
        raise PedidoNoCompletado('Solo se pueden calificar pedidos completados.')
    if CalificacionProveedor.objects.filter(pedido=pedido, tecnico=tecnico).exists():
        raise CalificacionDuplicada('Ya calificaste este pedido.')


def validar_calificacion_tecnico(*, pedido, proveedor):
    if pedido.proveedor_id != proveedor.pk:
        raise ActorInvalido('El pedido no pertenece al proveedor.')
    if pedido.estado != 'completado':
        raise PedidoNoCompletado('Solo se pueden calificar pedidos completados.')
    if CalificacionTecnico.objects.filter(pedido=pedido, proveedor=proveedor).exists():
        raise CalificacionDuplicada('Ya calificaste este pedido.')


@transaction.atomic
def calificar_proveedor(*, pedido, tecnico, estrellas, comentario=''):
    pedido = Pedido.objects.select_for_update().select_related('proveedor').get(pk=pedido.pk)
    validar_calificacion_proveedor(pedido=pedido, tecnico=tecnico)
    try:
        return CalificacionProveedor.objects.create(
            tecnico=tecnico,
            proveedor=pedido.proveedor,
            pedido=pedido,
            estrellas=estrellas,
            comentario=comentario,
        )
    except IntegrityError as error:
        raise CalificacionDuplicada('Ya calificaste este pedido.') from error


@transaction.atomic
def calificar_tecnico(*, pedido, proveedor, puntualidad, trato, comentario_privado=''):
    pedido = Pedido.objects.select_for_update().select_related('tecnico__usuario').get(pk=pedido.pk)
    validar_calificacion_tecnico(pedido=pedido, proveedor=proveedor)
    try:
        return CalificacionTecnico.objects.create(
            proveedor=proveedor,
            tecnico=pedido.tecnico,
            pedido=pedido,
            puntualidad=puntualidad,
            trato=trato,
            comentario_privado=comentario_privado,
        )
    except IntegrityError as error:
        raise CalificacionDuplicada('Ya calificaste este pedido.') from error
