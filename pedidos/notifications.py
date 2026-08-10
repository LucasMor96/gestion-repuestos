import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _send_transactional_mail(subject, message, recipient_list):
    """Envia usando el backend de email configurado en Django."""
    try:
        return send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            'No se pudo enviar email transaccional "%s" a %s',
            subject,
            ', '.join(recipient_list),
        )
        return 0

def notificar_proveedor_nuevo_pedido(pedido):
    """Envia email al proveedor cuando llega un nuevo pedido."""
    comprobante = ''
    if pedido.forma_pago == 'transferencia':
        comprobante = '  Comprobante: disponible en el detalle del pedido\n'

    _send_transactional_mail(
        subject=f'[Repuestos] Nuevo pedido #{pedido.id} - {pedido.producto.nombre}',
        message=(
            f'Hola {pedido.proveedor.usuario.first_name},\n\n'
            f'Recibiste un nuevo pedido en la plataforma:\n\n'
            f'  Producto : {pedido.producto.nombre}\n'
            f'  Cantidad : {pedido.cantidad}\n'
            f'  Monto    : ${pedido.monto_total}\n'
            f'  Entrega  : {pedido.get_forma_entrega_display()}\n'
            f'  Pago     : {pedido.get_forma_pago_display()}\n'
            f'{comprobante}'
            f'  Tecnico  : {pedido.tecnico.usuario.get_full_name()}\n'
            f'  Telefono : {pedido.tecnico.telefono or "No informado"}\n\n'
            f'Ingresa a la plataforma para aceptar o rechazar el pedido.\n'
        ),
        recipient_list=[pedido.proveedor.usuario.email],
    )

def notificar_tecnico_estado(pedido):
    """Envia email al tecnico cuando el proveedor cambia el estado de su pedido."""
    _send_transactional_mail(
        subject=f'[Repuestos] Pedido #{pedido.id} - {pedido.get_estado_display()}',
        message=(
            f'Hola {pedido.tecnico.usuario.first_name},\n\n'
            f'Tu pedido fue actualizado:\n\n'
            f'  Producto  : {pedido.producto.nombre}\n'
            f'  Estado    : {pedido.get_estado_display()}\n'
            f'  Proveedor : {pedido.proveedor.nombre_negocio}\n'
            + (
                f'  Retiro hasta: {pedido.fecha_limite_retiro.strftime("%d/%m/%Y %H:%M")}\n'
                if pedido.fecha_limite_retiro else ''
            )
            + (f'  Mensaje   : {pedido.respuesta_proveedor}\n' if pedido.respuesta_proveedor else '')
            + '\nIngresa a la plataforma para ver el detalle de tus pedidos.\n'
        ),
        recipient_list=[pedido.tecnico.usuario.email],
    )

def notificar_pedido_confirmado(pedido):
    """Envia email a tecnico y proveedor cuando el pedido queda completado."""
    _send_transactional_mail(
        subject=f'[Repuestos] Pedido #{pedido.id} confirmado',
        message=(
            f'El pedido #{pedido.id} fue confirmado como completado.\n\n'
            f'  Producto  : {pedido.producto.nombre}\n'
            f'  Cantidad  : {pedido.cantidad}\n'
            f'  Monto     : ${pedido.monto_total}\n'
            f'  Entrega   : {pedido.get_forma_entrega_display()}\n'
            f'  Pago      : {pedido.get_forma_pago_display()}\n'
            f'  Proveedor : {pedido.proveedor.nombre_negocio}\n'
            f'  Tecnico   : {pedido.tecnico.usuario.get_full_name()}\n\n'
            f'Ya pueden ingresar a la plataforma para calificar la operacion.\n'
        ),
        recipient_list=[
            pedido.tecnico.usuario.email,
            pedido.proveedor.usuario.email,
        ],
    )
