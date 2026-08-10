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

def notificar_credito_asignado(credito):
    _send_transactional_mail(
        subject=f'[Repuestos] Credito comercial asignado - {credito.proveedor.nombre_negocio}',
        message=(
            f'Hola {credito.tecnico.usuario.first_name},\n\n'
            f'{credito.proveedor.nombre_negocio} te asigno un credito comercial:\n\n'
            f'  Limite disponible: ${credito.limite}\n\n'
            f'Ya podes usarlo al hacer pedidos con este proveedor.\n'
        ),
        recipient_list=[credito.tecnico.usuario.email],
    )

def notificar_alerta_credito(credito):
    _send_transactional_mail(
        subject=f'[Repuestos] Alerta: limite de credito con {credito.proveedor.nombre_negocio}',
        message=(
            f'Hola {credito.tecnico.usuario.first_name},\n\n'
            f'Usaste el {credito.porcentaje_usado}% de tu credito con {credito.proveedor.nombre_negocio}:\n\n'
            f'  Limite total     : ${credito.limite}\n'
            f'  Saldo usado      : ${credito.saldo_usado}\n'
            f'  Saldo disponible : ${credito.saldo_disponible}\n\n'
            f'Por favor, regulariza tu deuda para seguir usando el credito.\n'
        ),
        recipient_list=[credito.tecnico.usuario.email],
    )

def notificar_deuda_saldada(credito):
    _send_transactional_mail(
        subject=f'[Repuestos] Tu deuda con {credito.proveedor.nombre_negocio} fue saldada',
        message=(
            f'Hola {credito.tecnico.usuario.first_name},\n\n'
            f'{credito.proveedor.nombre_negocio} marco tu deuda como saldada.\n\n'
            f'Tu credito disponible se restablecio. Limite: ${credito.limite}\n'
        ),
        recipient_list=[credito.tecnico.usuario.email],
    )

def notificar_credito_revocado(credito):
    _send_transactional_mail(
        subject=f'[Repuestos] Tu credito con {credito.proveedor.nombre_negocio} fue revocado',
        message=(
            f'Hola {credito.tecnico.usuario.first_name},\n\n'
            f'{credito.proveedor.nombre_negocio} revoco tu credito comercial.\n\n'
            f'Si tenes saldo pendiente, contacta al proveedor para regularizar tu situacion.\n'
        ),
        recipient_list=[credito.tecnico.usuario.email],
    )
