from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .exceptions import CreditoNoDisponible, DeudaInexistente, SaldoInsuficiente
from .models import Credito, PagoCredito


@transaction.atomic
def reservar_saldo(*, proveedor, tecnico, monto):
    try:
        credito = Credito.objects.select_for_update().get(
            proveedor=proveedor,
            tecnico=tecnico,
            activo=True,
        )
    except Credito.DoesNotExist as error:
        raise CreditoNoDisponible('No existe credito comercial activo.') from error
    if monto > credito.saldo_disponible:
        raise SaldoInsuficiente(disponible=credito.saldo_disponible, solicitado=monto)
    credito.saldo_usado += Decimal(monto)
    credito.save(update_fields=['saldo_usado'])
    return credito


@transaction.atomic
def liberar_saldo(*, proveedor, tecnico, monto, ciclo):
    try:
        credito = Credito.objects.select_for_update().get(
            proveedor=proveedor,
            tecnico=tecnico,
        )
    except Credito.DoesNotExist:
        return None
    # Una cancelacion de un ciclo ya saldado no libera deuda del ciclo actual.
    if credito.ciclo != ciclo:
        return credito
    credito.saldo_usado = max(Decimal('0'), credito.saldo_usado - Decimal(monto))
    credito.save(update_fields=['saldo_usado'])
    return credito


@transaction.atomic
def asignar_credito(*, proveedor, tecnico, limite):
    credito, _ = Credito.objects.select_for_update().get_or_create(
        proveedor=proveedor,
        tecnico=tecnico,
        defaults={'limite': limite, 'activo': True},
    )
    credito.limite = limite
    credito.activo = True
    credito.save(update_fields=['limite', 'activo'])
    return credito


@transaction.atomic
def revocar_credito(*, credito):
    credito = Credito.objects.select_for_update(of=('self',)).select_related(
        'tecnico__usuario', 'proveedor'
    ).get(pk=credito.pk)
    credito.activo = False
    credito.save(update_fields=['activo'])
    return credito


@transaction.atomic
def saldar_deuda(*, credito):
    credito = Credito.objects.select_for_update(of=('self',)).select_related(
        'tecnico__usuario', 'proveedor'
    ).get(pk=credito.pk)
    if credito.saldo_usado <= 0:
        raise DeudaInexistente('Este tecnico no tiene deuda pendiente.')
    credito.saldo_usado = Decimal('0')
    credito.ciclo += 1
    credito.save(update_fields=['saldo_usado', 'ciclo'])
    return credito


@transaction.atomic
def solicitar_pago(*, credito):
    credito = Credito.objects.select_for_update().select_related(
        'proveedor', 'tecnico__usuario'
    ).get(pk=credito.pk)
    if credito.saldo_usado <= 0:
        raise DeudaInexistente('Este técnico no tiene deuda pendiente.')
    if PagoCredito.objects.filter(credito=credito, ciclo=credito.ciclo, estado='pendiente').exists():
        raise ValueError('Ya existe una solicitud de pago pendiente para este crédito.')
    return PagoCredito.objects.create(credito=credito, monto=credito.saldo_usado, ciclo=credito.ciclo)


@transaction.atomic
def resolver_pago(*, pago, confirmado):
    pago = PagoCredito.objects.select_for_update().select_related('credito').get(pk=pago.pk)
    if pago.estado != 'pendiente':
        return pago
    credito = Credito.objects.select_for_update().get(pk=pago.credito_id)
    if confirmado and pago.ciclo == credito.ciclo and credito.saldo_usado > 0:
        credito.saldo_usado = Decimal('0')
        credito.ciclo += 1
        credito.save(update_fields=['saldo_usado', 'ciclo'])
    pago.estado = 'confirmado' if confirmado else 'rechazado'
    pago.fecha_resolucion = timezone.now()
    pago.save(update_fields=['estado', 'fecha_resolucion'])
    return pago
