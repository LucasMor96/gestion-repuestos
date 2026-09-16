from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.usuarios.models import Tecnico
from apps.usuarios.utils import get_proveedor_o_403, get_tecnico_o_403

from .exceptions import DeudaInexistente
from .forms import AsignarCreditoForm
from .models import Credito, PagoCredito
from .selectors import (
    buscar_tecnicos_aprobados,
    creditos_activos_proveedor,
    creditos_activos_tecnico,
    deudas_proveedor,
    pedidos_de_credito,
)
from .services import asignar_credito as asignar_credito_servicio
from .services import revocar_credito as revocar_credito_servicio
from .services import saldar_deuda
from .services import resolver_pago, solicitar_pago
from .selectors import pagos_pendientes_proveedor


@login_required(login_url='login')
def mis_creditos(request):
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')
    return render(request, 'creditos/mis_creditos.html', {
        'creditos': creditos_activos_tecnico(tecnico),
    })


@login_required(login_url='login')
def pagar_credito(request, pk):
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')
    credito = get_object_or_404(
        Credito.objects.select_related('proveedor'), pk=pk, tecnico=tecnico, activo=True
    )
    pago_pendiente = credito.pagos.filter(ciclo=credito.ciclo, estado='pendiente').first()
    if request.method == 'POST':
        try:
            solicitar_pago(credito=credito)
        except ValueError as error:
            messages.info(request, str(error))
        except DeudaInexistente:
            messages.warning(request, 'Este crédito no tiene deuda pendiente.')
        else:
            messages.success(request, 'Avisamos al proveedor que realizaste la transferencia. Esperá su confirmación.')
        return redirect('mis_creditos')
    return render(request, 'creditos/pagar_credito.html', {
        'credito': credito,
        'pago_pendiente': pago_pendiente,
    })


@login_required(login_url='login')
def gestionar_creditos_proveedor(request):
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')
    return render(request, 'creditos/gestionar_creditos_proveedor.html', {
        'creditos': creditos_activos_proveedor(proveedor),
        'pagos_pendientes': pagos_pendientes_proveedor(proveedor),
    })


@login_required(login_url='login')
def asignar_credito(request):
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')
    busqueda = request.GET.get('q', '').strip()
    tecnicos_encontrados = buscar_tecnicos_aprobados(busqueda)
    tecnico_pk = request.GET.get('tecnico', '').strip()
    tecnico_sel = get_object_or_404(Tecnico, pk=tecnico_pk, is_approved=True) if tecnico_pk else None
    credito_existente = (
        Credito.objects.filter(proveedor=proveedor, tecnico=tecnico_sel).first()
        if tecnico_sel else None
    )
    if request.method == 'POST' and tecnico_sel:
        form = AsignarCreditoForm(request.POST, instance=credito_existente)
        if form.is_valid():
            credito = asignar_credito_servicio(
                proveedor=proveedor,
                tecnico=tecnico_sel,
                limite=form.cleaned_data['limite'],
            )
            messages.success(
                request,
                f'Crédito de ${credito.limite} asignado a '
                f'{tecnico_sel.usuario.get_full_name()} correctamente.',
            )
            return redirect('gestionar_creditos_proveedor')
    else:
        form = AsignarCreditoForm(instance=credito_existente) if tecnico_sel else None
    return render(request, 'creditos/asignar_credito.html', {
        'busqueda': busqueda,
        'tecnicos_encontrados': tecnicos_encontrados,
        'tecnico_sel': tecnico_sel,
        'credito_existente': credito_existente,
        'form': form,
    })


@login_required(login_url='login')
@require_POST
def revocar_credito(request, pk):
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')
    credito = get_object_or_404(Credito, pk=pk, proveedor=proveedor)
    credito = revocar_credito_servicio(credito=credito)
    messages.success(
        request,
        f'Crédito de {credito.tecnico.usuario.get_full_name()} revocado correctamente.',
    )
    return redirect('gestionar_creditos_proveedor')


@login_required(login_url='login')
def deudas_tecnicos(request):
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')
    return render(request, 'creditos/deudas_tecnicos.html', {
        'deudas': deudas_proveedor(proveedor),
    })


@login_required(login_url='login')
def detalle_deuda_tecnico(request, pk):
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')
    credito = get_object_or_404(Credito, pk=pk, proveedor=proveedor)
    return render(request, 'creditos/detalle_deuda_tecnico.html', {
        'credito': credito,
        'pedidos_credito': pedidos_de_credito(
            proveedor=proveedor, tecnico=credito.tecnico
        ),
    })


@login_required(login_url='login')
@require_POST
def marcar_deuda_saldada(request, pk):
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')
    credito = get_object_or_404(Credito, pk=pk, proveedor=proveedor)
    try:
        credito = saldar_deuda(credito=credito)
    except DeudaInexistente:
        messages.warning(request, 'Este técnico no tiene deuda pendiente.')
    else:
        messages.success(
            request,
            f'Deuda de {credito.tecnico.usuario.get_full_name()} marcada como saldada. '
            'El crédito disponible se restableció.',
        )
    return redirect('deudas_tecnicos')


@login_required(login_url='login')
@require_POST
def confirmar_pago_credito(request, pk):
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')
    pago = get_object_or_404(PagoCredito, pk=pk, credito__proveedor=proveedor)
    resolver_pago(pago=pago, confirmado=True)
    messages.success(request, 'Pago confirmado. La deuda fue saldada y el crédito quedó disponible.')
    return redirect('gestionar_creditos_proveedor')


@login_required(login_url='login')
@require_POST
def rechazar_pago_credito(request, pk):
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')
    pago = get_object_or_404(PagoCredito, pk=pk, credito__proveedor=proveedor)
    resolver_pago(pago=pago, confirmado=False)
    messages.info(request, 'La solicitud de pago fue rechazada. El técnico deberá verificar la transferencia.')
    return redirect('gestionar_creditos_proveedor')
