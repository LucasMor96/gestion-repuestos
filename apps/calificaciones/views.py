from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.pedidos.models import Pedido
from apps.usuarios.utils import get_proveedor_o_403, get_tecnico_o_403

from .exceptions import CalificacionDuplicada, PedidoNoCompletado
from .forms import CalificacionProveedorForm, CalificacionTecnicoForm
from .services import (
    calificar_proveedor as calificar_proveedor_servicio,
    calificar_tecnico as calificar_tecnico_servicio,
    validar_calificacion_proveedor,
    validar_calificacion_tecnico,
)


@login_required(login_url='login')
def calificar_proveedor(request, pedido_pk):
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')
    pedido = get_object_or_404(Pedido, pk=pedido_pk, tecnico=tecnico)
    try:
        validar_calificacion_proveedor(pedido=pedido, tecnico=tecnico)
    except PedidoNoCompletado:
        messages.error(request, 'Solo podés calificar pedidos completados.')
        return redirect('mis_pedidos')
    except CalificacionDuplicada:
        messages.warning(request, 'Ya calificaste este pedido.')
        return redirect('mis_pedidos')
    if request.method == 'POST':
        form = CalificacionProveedorForm(request.POST)
        if form.is_valid():
            try:
                calificacion = calificar_proveedor_servicio(
                    pedido=pedido, tecnico=tecnico, **form.cleaned_data
                )
            except CalificacionDuplicada:
                messages.warning(request, 'Ya calificaste este pedido.')
                return redirect('mis_pedidos')
            estrellas = calificacion.estrellas
            messages.success(
                request,
                f'Calificaste a {pedido.proveedor.nombre_negocio} con {estrellas} '
                f'estrella{"s" if estrellas != 1 else ""}. ¡Gracias por tu opinión!',
            )
            return redirect('mis_pedidos')
    else:
        form = CalificacionProveedorForm()
    return render(request, 'calificaciones/calificar_proveedor.html', {
        'form': form, 'pedido': pedido,
    })


@login_required(login_url='login')
def calificar_tecnico(request, pedido_pk):
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')
    pedido = get_object_or_404(Pedido, pk=pedido_pk, proveedor=proveedor)
    try:
        validar_calificacion_tecnico(pedido=pedido, proveedor=proveedor)
    except PedidoNoCompletado:
        messages.error(request, 'Solo podés calificar técnicos con pedidos completados.')
        return redirect('pedidos_recibidos')
    except CalificacionDuplicada:
        messages.warning(request, 'Ya calificaste a este técnico por este pedido.')
        return redirect('pedidos_recibidos')
    if request.method == 'POST':
        form = CalificacionTecnicoForm(request.POST)
        if form.is_valid():
            try:
                calificar_tecnico_servicio(
                    pedido=pedido, proveedor=proveedor, **form.cleaned_data
                )
            except CalificacionDuplicada:
                messages.warning(request, 'Ya calificaste a este técnico por este pedido.')
                return redirect('pedidos_recibidos')
            messages.success(
                request,
                f'Calificaste al técnico {pedido.tecnico.usuario.get_full_name()} correctamente. ¡Gracias!',
            )
            return redirect('pedidos_recibidos')
    else:
        form = CalificacionTecnicoForm()
    return render(request, 'calificaciones/calificar_tecnico.html', {
        'form': form, 'pedido': pedido,
    })
