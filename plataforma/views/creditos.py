from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import AsignarCreditoForm
from ..models import Credito, Pedido, Tecnico
from .notifications import (
    notificar_credito_asignado,
    notificar_credito_revocado,
    notificar_deuda_saldada,
)
from .utils import get_proveedor_o_403, get_tecnico_o_403


@login_required(login_url='login')
def mis_creditos(request):
    """Técnico ve sus créditos disponibles con cada proveedor (US-10)."""
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')

    creditos = tecnico.creditos.select_related('proveedor').filter(activo=True)
    return render(request, 'plataforma/mis_creditos.html', {'creditos': creditos})


@login_required(login_url='login')
def gestionar_creditos_proveedor(request):
    """Proveedor ve y administra los créditos asignados a técnicos (US-11)."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    creditos = proveedor.creditos.select_related('tecnico__usuario').filter(activo=True).order_by(
        'tecnico__usuario__last_name'
    )
    return render(request, 'plataforma/gestionar_creditos_proveedor.html', {'creditos': creditos})


@login_required(login_url='login')
def asignar_credito(request):
    """Proveedor asigna o edita el límite de crédito de un técnico (US-11)."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    busqueda = request.GET.get('q', '').strip()
    tecnicos_encontrados = []

    if busqueda:
        try:
            pk = int(busqueda)
            tecnicos_encontrados = Tecnico.objects.filter(pk=pk, is_approved=True).select_related('usuario')
        except ValueError:
            tecnicos_encontrados = Tecnico.objects.filter(
                Q(usuario__first_name__icontains=busqueda) | Q(usuario__last_name__icontains=busqueda),
                is_approved=True,
            ).select_related('usuario')

    tecnico_pk = request.GET.get('tecnico', '').strip()
    tecnico_sel = None
    credito_existente = None

    if tecnico_pk:
        tecnico_sel = get_object_or_404(Tecnico, pk=tecnico_pk, is_approved=True)
        try:
            credito_existente = Credito.objects.get(proveedor=proveedor, tecnico=tecnico_sel)
        except Credito.DoesNotExist:
            pass

    if request.method == 'POST' and tecnico_sel:
        form = AsignarCreditoForm(request.POST, instance=credito_existente)
        if form.is_valid():
            try:
                credito = form.save(commit=False)
                credito.proveedor = proveedor
                credito.tecnico = tecnico_sel
                credito.activo = True
                credito.save()
                notificar_credito_asignado(credito)
                messages.success(
                    request,
                    f'Crédito de ${credito.limite} asignado a '
                    f'{tecnico_sel.usuario.get_full_name()} correctamente.'
                )
                return redirect('gestionar_creditos_proveedor')
            except Exception:
                messages.error(request, 'Ocurrió un error al asignar el crédito. Intentá de nuevo.')
    else:
        form = AsignarCreditoForm(instance=credito_existente) if tecnico_sel else None

    return render(request, 'plataforma/asignar_credito.html', {
        'busqueda': busqueda,
        'tecnicos_encontrados': tecnicos_encontrados,
        'tecnico_sel': tecnico_sel,
        'credito_existente': credito_existente,
        'form': form,
    })


@login_required(login_url='login')
def revocar_credito(request, pk):
    """Proveedor revoca el crédito de un técnico (US-11)."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    credito = get_object_or_404(Credito, pk=pk, proveedor=proveedor)

    if request.method == 'POST':
        try:
            credito.activo = False
            credito.save()
            notificar_credito_revocado(credito)
            messages.success(
                request,
                f'Crédito de {credito.tecnico.usuario.get_full_name()} revocado correctamente.'
            )
        except Exception:
            messages.error(request, 'Ocurrió un error al revocar el crédito. Intentá de nuevo.')

    return redirect('gestionar_creditos_proveedor')


@login_required(login_url='login')
def deudas_tecnicos(request):
    """Proveedor consulta qué técnicos tienen deuda pendiente (US-12)."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    deudas = (
        proveedor.creditos
        .select_related('tecnico__usuario')
        .filter(saldo_usado__gt=0)
        .order_by('-saldo_usado')
    )
    return render(request, 'plataforma/deudas_tecnicos.html', {'deudas': deudas})


@login_required(login_url='login')
def detalle_deuda_tecnico(request, pk):
    """Proveedor ve el detalle de pedidos que componen la deuda de un técnico (US-12)."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    credito = get_object_or_404(Credito, pk=pk, proveedor=proveedor)
    pedidos_credito = (
        Pedido.objects
        .filter(proveedor=proveedor, tecnico=credito.tecnico, usa_credito=True)
        .exclude(estado__in=['cancelado', 'rechazado'])
        .order_by('-fecha_creacion')
    )
    return render(request, 'plataforma/detalle_deuda_tecnico.html', {
        'credito': credito,
        'pedidos_credito': pedidos_credito,
    })


@login_required(login_url='login')
def marcar_deuda_saldada(request, pk):
    """Proveedor marca como saldada la deuda de un técnico (US-12)."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    credito = get_object_or_404(Credito, pk=pk, proveedor=proveedor)

    if request.method == 'POST':
        try:
            if credito.saldo_usado <= 0:
                messages.warning(request, 'Este técnico no tiene deuda pendiente.')
            else:
                credito.saldo_usado = 0
                credito.save()
                notificar_deuda_saldada(credito)
                messages.success(
                    request,
                    f'Deuda de {credito.tecnico.usuario.get_full_name()} marcada como saldada. '
                    f'El crédito disponible se restableció.'
                )
        except Exception:
            messages.error(request, 'Ocurrió un error al saldar la deuda. Intentá de nuevo.')

    return redirect('deudas_tecnicos')
