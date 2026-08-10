from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.catalogo.models import Producto
from apps.creditos.services import liberar_saldo, reservar_saldo

from .exceptions import EstadoPedidoInvalido, StockInsuficiente
from .models import Pedido
from .notifications import (
    notificar_pedido_confirmado,
    notificar_proveedor_nuevo_pedido,
    notificar_tecnico_estado,
)


def calcular_costo_envio(forma_entrega, cantidad):
    if forma_entrega != 'envio':
        return Decimal('0')
    return Decimal('3500') + Decimal(max(cantidad - 1, 0)) * Decimal('900')


def _notas_con_envio(notas, datos):
    if datos.get('forma_entrega') != 'envio':
        return notas
    franjas = {
        'manana': 'Mañana, 9 a 13 hs',
        'tarde': 'Tarde, 13 a 18 hs',
        'noche': 'Último reparto, 18 a 21 hs',
    }
    bloque = (
        'Datos de envio:\n'
        f'- Dirección: {datos.get("direccion_envio")}\n'
        f'- Teléfono: {datos.get("telefono_contacto")}\n'
        f'- Franja horaria: {franjas.get(datos.get("franja_horaria"), "")}'
    )
    notas = (notas or '').strip()
    return f'{notas}\n\n{bloque}' if notas else bloque


@transaction.atomic
def crear_pedido(*, tecnico, producto, datos):
    producto = Producto.objects.select_for_update().select_related('proveedor').get(pk=producto.pk)
    cantidad = datos['cantidad']
    if not producto.disponible or producto.stock < cantidad:
        raise StockInsuficiente(disponible=producto.stock, solicitado=cantidad)
    usa_credito = datos['forma_pago'] == 'credito_comercial'
    monto_total = producto.precio * cantidad + calcular_costo_envio(datos['forma_entrega'], cantidad)
    if usa_credito:
        reservar_saldo(
            proveedor=producto.proveedor,
            tecnico=tecnico,
            monto=monto_total,
        )
    pedido = Pedido.objects.create(
        tecnico=tecnico,
        proveedor=producto.proveedor,
        producto=producto,
        cantidad=cantidad,
        forma_entrega=datos['forma_entrega'],
        forma_pago=datos['forma_pago'],
        comprobante_transferencia=datos.get('comprobante_transferencia'),
        notas=_notas_con_envio(datos.get('notas'), datos),
        monto_total=monto_total,
        estado='pendiente',
        usa_credito=usa_credito,
    )
    transaction.on_commit(lambda: notificar_proveedor_nuevo_pedido(pedido))
    return pedido


def _pedido_bloqueado(pedido):
    return Pedido.objects.select_for_update().con_relaciones().get(pk=pedido.pk)


def _exigir_estado(pedido, estado):
    if pedido.estado != estado:
        raise EstadoPedidoInvalido(f'El pedido debe estar en estado {estado}.')


@transaction.atomic
def aceptar_pedido(*, pedido, respuesta=''):
    pedido = _pedido_bloqueado(pedido)
    _exigir_estado(pedido, 'pendiente')
    producto = Producto.objects.select_for_update().get(pk=pedido.producto_id)
    if producto.stock < pedido.cantidad:
        raise StockInsuficiente(disponible=producto.stock, solicitado=pedido.cantidad)
    producto.stock -= pedido.cantidad
    producto.save(update_fields=['stock'])
    pedido.estado = 'aceptado'
    pedido.respuesta_proveedor = respuesta or None
    pedido.save(update_fields=['estado', 'respuesta_proveedor', 'fecha_actualizacion'])
    transaction.on_commit(lambda: notificar_tecnico_estado(pedido))
    return pedido


@transaction.atomic
def rechazar_pedido(*, pedido, respuesta='', alternativa=False):
    pedido = _pedido_bloqueado(pedido)
    _exigir_estado(pedido, 'pendiente')
    pedido.estado = 'rechazado'
    pedido.respuesta_proveedor = (
        f'Alternativa propuesta: {respuesta}' if alternativa else (respuesta or None)
    )
    pedido.save(update_fields=['estado', 'respuesta_proveedor', 'fecha_actualizacion'])
    if pedido.usa_credito:
        liberar_saldo(
            proveedor=pedido.proveedor,
            tecnico=pedido.tecnico,
            monto=pedido.monto_total,
        )
    transaction.on_commit(lambda: notificar_tecnico_estado(pedido))
    return pedido


@transaction.atomic
def cancelar_pedido(*, pedido):
    pedido = _pedido_bloqueado(pedido)
    _exigir_estado(pedido, 'pendiente')
    pedido.estado = 'cancelado'
    pedido.save(update_fields=['estado', 'fecha_actualizacion'])
    if pedido.usa_credito:
        liberar_saldo(
            proveedor=pedido.proveedor,
            tecnico=pedido.tecnico,
            monto=pedido.monto_total,
        )
    return pedido


@transaction.atomic
def completar_pedido(*, pedido):
    pedido = _pedido_bloqueado(pedido)
    _exigir_estado(pedido, 'aceptado')
    pedido.estado = 'completado'
    pedido.save(update_fields=['estado', 'fecha_actualizacion'])
    transaction.on_commit(lambda: notificar_pedido_confirmado(pedido))
    return pedido


@transaction.atomic
def cancelar_retiros_vencidos(pedidos):
    ids = list(pedidos.values_list('pk', flat=True)) if hasattr(pedidos, 'values_list') else [p.pk for p in pedidos]
    vencidos = Pedido.objects.select_for_update().filter(
        pk__in=ids,
        estado='aceptado',
        forma_entrega='retiro',
        fecha_actualizacion__lte=timezone.now() - timedelta(hours=24),
    ).select_related('producto', 'proveedor', 'tecnico')
    cantidad = 0
    for pedido in vencidos:
        producto = Producto.objects.select_for_update().get(pk=pedido.producto_id)
        producto.stock += pedido.cantidad
        producto.save(update_fields=['stock'])
        pedido.estado = 'cancelado'
        pedido.respuesta_proveedor = (
            'Compra cancelada automaticamente: no se retiro dentro de las 24 hs posteriores a la confirmacion.'
        )
        pedido.save(update_fields=['estado', 'respuesta_proveedor', 'fecha_actualizacion'])
        if pedido.usa_credito:
            liberar_saldo(
                proveedor=pedido.proveedor,
                tecnico=pedido.tecnico,
                monto=pedido.monto_total,
            )
        cantidad += 1
    return cantidad
