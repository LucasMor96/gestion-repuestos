from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.catalogo.models import Producto
from apps.creditos.services import asignar_credito, liberar_saldo, reservar_saldo
from apps.usuarios.models import Proveedor
from apps.usuarios.utils import perfil_aprobado

from .exceptions import EstadoPedidoInvalido, FormaPagoInvalida, LimiteCreditoInvalido, ProveedorNoHabilitado, StockInsuficiente
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
    if datos.get('forma_pago') not in dict(Pedido.FORMA_PAGO_CHOICES):
        raise FormaPagoInvalida('Elegí una forma de pago disponible.')
    clave_operacion = UUID(str(datos['clave_operacion']))
    # Serializa envios del mismo producto antes de comprobar la clave y reservar saldo.
    producto = Producto.objects.select_for_update(of=('self',)).get(pk=producto.pk)
    existente = Pedido.objects.filter(
        tecnico=tecnico, producto=producto, clave_operacion=clave_operacion,
    ).first()
    if existente is not None:
        return existente
    # Revalida y mantiene estable la habilitacion hasta confirmar la compra.
    proveedor = Proveedor.objects.select_related('usuario').select_for_update(
        of=('self', 'usuario'), no_key=True,
    ).get(pk=producto.proveedor_id)
    if not perfil_aprobado(proveedor):
        raise ProveedorNoHabilitado('Este proveedor no está habilitado para recibir nuevas compras.')
    producto.proveedor = proveedor
    cantidad = datos['cantidad']
    if not producto.disponible or producto.stock < cantidad:
        raise StockInsuficiente(disponible=producto.stock, solicitado=cantidad)
    usa_credito = datos['forma_pago'] == 'credito_comercial'
    monto_total = producto.precio * cantidad + calcular_costo_envio(datos['forma_entrega'], cantidad)
    credito = None
    if usa_credito:
        credito = reservar_saldo(
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
        ciclo_credito=credito.ciclo if credito else 0,
        clave_operacion=clave_operacion,
    )
    transaction.on_commit(lambda: notificar_proveedor_nuevo_pedido(pedido))
    return pedido


def _pedido_bloqueado(pedido):
    return Pedido.objects.select_for_update(of=('self',)).con_relaciones().get(pk=pedido.pk)


def _exigir_estado(pedido, estado):
    if pedido.estado != estado:
        raise EstadoPedidoInvalido(f'El pedido debe estar en estado {estado}.')


@transaction.atomic
def aceptar_pedido(*, pedido, respuesta='', limite_credito=None):
    pedido = _pedido_bloqueado(pedido)
    _exigir_estado(pedido, 'pendiente')
    producto = Producto.objects.select_for_update().get(pk=pedido.producto_id)
    if producto.stock < pedido.cantidad:
        raise StockInsuficiente(disponible=producto.stock, solicitado=pedido.cantidad)
    if pedido.forma_pago == 'solicitud_credito':
        if limite_credito is None or limite_credito <= 0:
            raise LimiteCreditoInvalido('Indicá un límite de crédito mayor a cero.')
        # Otorgamiento, reserva y aceptacion se confirman juntos o se revierten juntos.
        asignar_credito(
            proveedor=pedido.proveedor, tecnico=pedido.tecnico, limite=limite_credito,
        )
        credito = reservar_saldo(
            proveedor=pedido.proveedor, tecnico=pedido.tecnico, monto=pedido.monto_total,
        )
        pedido.usa_credito = True
        pedido.ciclo_credito = credito.ciclo
    producto.stock -= pedido.cantidad
    producto.save(update_fields=['stock'])
    pedido.estado = 'aceptado'
    pedido.respuesta_proveedor = respuesta or None
    pedido.save(update_fields=[
        'estado', 'respuesta_proveedor', 'fecha_actualizacion', 'usa_credito', 'ciclo_credito',
    ])
    transaction.on_commit(lambda: notificar_tecnico_estado(pedido))
    return pedido


@transaction.atomic
def rechazar_pedido(*, pedido, respuesta='', alternativa=False, producto_alternativo=None):
    pedido = _pedido_bloqueado(pedido)
    _exigir_estado(pedido, 'pendiente')
    pedido.estado = 'rechazado'
    pedido.producto_alternativo = producto_alternativo if alternativa else None
    pedido.respuesta_proveedor = respuesta or None
    pedido.save(update_fields=[
        'estado', 'producto_alternativo', 'respuesta_proveedor', 'fecha_actualizacion',
    ])
    if pedido.usa_credito:
        liberar_saldo(
            proveedor=pedido.proveedor,
            tecnico=pedido.tecnico,
            monto=pedido.monto_total,
            ciclo=pedido.ciclo_credito,
        )
    transaction.on_commit(lambda: notificar_tecnico_estado(pedido))
    return pedido


@transaction.atomic
def cancelar_pedido(*, pedido, respuesta='', notificar=False):
    pedido = _pedido_bloqueado(pedido)
    _exigir_estado(pedido, 'pendiente')
    pedido.estado = 'cancelado'
    pedido.respuesta_proveedor = respuesta or None
    pedido.save(update_fields=['estado', 'respuesta_proveedor', 'fecha_actualizacion'])
    if pedido.usa_credito:
        liberar_saldo(
            proveedor=pedido.proveedor,
            tecnico=pedido.tecnico,
            monto=pedido.monto_total,
            ciclo=pedido.ciclo_credito,
        )
    if notificar:
        transaction.on_commit(lambda: notificar_tecnico_estado(pedido))
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
    vencidos = Pedido.objects.select_for_update(of=('self',)).filter(
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
                ciclo=pedido.ciclo_credito,
            )
        cantidad += 1
    return cantidad
