from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import CalificacionProveedorForm, CalificacionTecnicoForm
from ..models import Pedido
from .utils import get_proveedor_o_403, get_tecnico_o_403


@login_required(login_url='login')
def calificar_proveedor(request, pedido_pk):
    """TÃ©cnico califica a un proveedor tras un pedido completado (US-13)."""
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')

    pedido = get_object_or_404(Pedido, pk=pedido_pk, tecnico=tecnico)

    if pedido.estado != 'completado':
        messages.error(request, 'Solo podÃ©s calificar pedidos completados.')
        return redirect('mis_pedidos')

    if pedido.calificacion_proveedor.exists():
        messages.warning(request, 'Ya calificaste este pedido.')
        return redirect('mis_pedidos')

    if request.method == 'POST':
        form = CalificacionProveedorForm(request.POST)
        if form.is_valid():
            try:
                calificacion = form.save(commit=False)
                calificacion.tecnico = tecnico
                calificacion.proveedor = pedido.proveedor
                calificacion.pedido = pedido
                calificacion.save()
                estrellas = calificacion.estrellas
                messages.success(
                    request,
                    f'Calificaste a {pedido.proveedor.nombre_negocio} con {estrellas} '
                    f'estrella{"s" if estrellas != 1 else ""}. Â¡Gracias por tu opiniÃ³n!'
                )
                return redirect('mis_pedidos')
            except ValueError as error:
                messages.error(request, str(error))
            except Exception:
                messages.error(request, 'OcurriÃ³ un error al guardar la calificaciÃ³n. IntentÃ¡ de nuevo.')
    else:
        form = CalificacionProveedorForm()

    return render(request, 'plataforma/calificar_proveedor.html', {
        'form': form,
        'pedido': pedido,
    })


@login_required(login_url='login')
def calificar_tecnico(request, pedido_pk):
    """Proveedor califica a un tÃ©cnico tras un pedido completado (US-14)."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    pedido = get_object_or_404(Pedido, pk=pedido_pk, proveedor=proveedor)

    if pedido.estado != 'completado':
        messages.error(request, 'Solo podÃ©s calificar tÃ©cnicos con pedidos completados.')
        return redirect('pedidos_recibidos')

    if pedido.calificacion_tecnico.exists():
        messages.warning(request, 'Ya calificaste a este tÃ©cnico por este pedido.')
        return redirect('pedidos_recibidos')

    if request.method == 'POST':
        form = CalificacionTecnicoForm(request.POST)
        if form.is_valid():
            try:
                calificacion = form.save(commit=False)
                calificacion.proveedor = proveedor
                calificacion.tecnico = pedido.tecnico
                calificacion.pedido = pedido
                calificacion.save()
                messages.success(
                    request,
                    f'Calificaste al tÃ©cnico {pedido.tecnico.usuario.get_full_name()} correctamente. Â¡Gracias!'
                )
                return redirect('pedidos_recibidos')
            except ValueError as error:
                messages.error(request, str(error))
            except Exception:
                messages.error(request, 'OcurriÃ³ un error al guardar la calificaciÃ³n. IntentÃ¡ de nuevo.')
    else:
        form = CalificacionTecnicoForm()

    return render(request, 'plataforma/calificar_tecnico.html', {
        'form': form,
        'pedido': pedido,
    })
