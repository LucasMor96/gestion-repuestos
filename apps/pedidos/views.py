from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalogo.models import Producto
from apps.creditos.exceptions import CreditoNoDisponible, SaldoInsuficiente
from apps.creditos.models import Credito
from apps.usuarios.utils import get_proveedor_o_403, get_tecnico_o_403

from .exceptions import EstadoPedidoInvalido, LimiteCreditoInvalido, ProveedorNoHabilitado, StockInsuficiente
from .exporters import exportar_historial_csv
from .forms import GestionarPedidoForm, PedidoForm
from .models import Pedido
from .selectors import historial_tecnico, pedidos_recibidos as seleccionar_recibidos, proveedores_del_historial
from .services import (
    aceptar_pedido,
    cancelar_pedido as cancelar_pedido_servicio,
    cancelar_retiros_vencidos,
    completar_pedido as completar_pedido_servicio,
    crear_pedido as crear_pedido_servicio,
    rechazar_pedido,
)


def _filtros_historial(request):
    return {
        'fecha_desde': request.GET.get('fecha_desde', '').strip(),
        'fecha_hasta': request.GET.get('fecha_hasta', '').strip(),
        'proveedor_id': request.GET.get('proveedor', '').strip(),
    }


@login_required(login_url='login')
def crear_pedido(request, producto_pk):
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')
    producto = get_object_or_404(Producto.objects.publicados(), pk=producto_pk)
    credito = Credito.objects.filter(
        proveedor=producto.proveedor, tecnico=tecnico, activo=True
    ).first()

    if request.method == 'POST':
        form = PedidoForm(request.POST, request.FILES, stock=producto.stock, tecnico=tecnico)
        valido = form.is_valid()
        clave = form.cleaned_data.get('clave_operacion')
        if clave and Pedido.objects.filter(
            tecnico=tecnico, producto=producto, clave_operacion=clave,
        ).exists():
            messages.info(request, 'Este pedido ya fue enviado correctamente.')
            return redirect('mis_pedidos')
        if valido:
            try:
                pedido = crear_pedido_servicio(
                    tecnico=tecnico,
                    producto=producto,
                    datos=form.cleaned_data,
                )
            except CreditoNoDisponible:
                messages.error(
                    request,
                    f'No tenés crédito comercial activo con {producto.proveedor.nombre_negocio}. '
                    'Elegí transferencia o MercadoPago simulado para continuar.',
                )
            except SaldoInsuficiente as error:
                messages.error(
                    request,
                    f'El monto del pedido (${error.solicitado}) supera tu crédito disponible '
                    f'(${error.disponible}) con {producto.proveedor.nombre_negocio}.',
                )
            except (StockInsuficiente, ProveedorNoHabilitado) as error:
                messages.error(request, str(error))
            except DatabaseError:
                messages.error(request, 'Ocurrió un error al procesar el pedido. Intentá de nuevo.')
            else:
                detalle_pago = ''
                if pedido.forma_pago == 'mercadopago':
                    detalle_pago = ' MercadoPago esta funcionando en modo simulado.'
                elif pedido.forma_pago == 'credito_comercial':
                    detalle_pago = ' Se usó tu crédito comercial disponible.'
                elif pedido.forma_pago == 'solicitud_credito':
                    detalle_pago = ' Tu solicitud de crédito quedó pendiente de aprobación del proveedor.'
                messages.success(
                    request,
                    f'Pedido #{pedido.id} enviado correctamente. '
                    f'Forma de pago: {pedido.get_forma_pago_display()}.'
                    f'{detalle_pago} {pedido.proveedor.nombre_negocio} recibira tu solicitud.',
                )
                return redirect('mis_pedidos')
    else:
        form = PedidoForm(stock=producto.stock, tecnico=tecnico)
    return render(request, 'pedidos/crear_pedido.html', {
        'form': form, 'producto': producto, 'credito': credito,
    })


@login_required(login_url='login')
def mis_pedidos(request):
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')
    filtros = _filtros_historial(request)
    cancelar_retiros_vencidos(tecnico.pedidos.all())
    pedidos = historial_tecnico(tecnico=tecnico, **filtros)
    proveedores = proveedores_del_historial(tecnico)
    return render(request, 'pedidos/mis_pedidos.html', {
        'pedidos': pedidos,
        'proveedores': proveedores,
        'hay_filtros': any(filtros.values()),
        'fecha_desde': filtros['fecha_desde'],
        'fecha_hasta': filtros['fecha_hasta'],
        'proveedor_id_sel': filtros['proveedor_id'],
    })


@login_required(login_url='login')
def exportar_historial(request):
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')
    pedidos = historial_tecnico(tecnico=tecnico, **_filtros_historial(request))
    return exportar_historial_csv(pedidos)


@login_required(login_url='login')
@require_POST
def cancelar_pedido(request, pk):
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')
    pedido = get_object_or_404(Pedido, pk=pk, tecnico=tecnico)
    try:
        cancelar_pedido_servicio(pedido=pedido)
    except EstadoPedidoInvalido:
        messages.error(request, 'Solo podés cancelar pedidos en estado pendiente.')
    else:
        messages.success(request, f'Pedido #{pedido.id} cancelado correctamente.')
    return redirect('mis_pedidos')


@login_required(login_url='login')
def pedidos_recibidos(request):
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')
    cancelar_retiros_vencidos(proveedor.pedidos_recibidos.all())
    return render(request, 'pedidos/pedidos_recibidos.html', {
        'pedidos': seleccionar_recibidos(proveedor),
    })


def _contexto_detalle_pedido(pedido, form=None):
    if form is None:
        initial = {}
        solicitud = pedido.forma_pago == 'solicitud_credito'
        if solicitud:
            credito = Credito.objects.filter(
                proveedor=pedido.proveedor, tecnico=pedido.tecnico,
            ).first()
            initial['limite_credito'] = (
                max(credito.limite, credito.saldo_usado + pedido.monto_total)
                if credito else pedido.monto_total
            )
        form = GestionarPedidoForm(solicitud_credito=solicitud, initial=initial)
    return {
        'pedido': pedido, 'form': form,
        'ya_calificado': pedido.calificacion_tecnico.exists(),
    }


@login_required(login_url='login')
def detalle_pedido_proveedor(request, pk):
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')
    pedido = get_object_or_404(Pedido.objects.con_relaciones(), pk=pk, proveedor=proveedor)
    vencido = cancelar_retiros_vencidos([pedido])
    if vencido:
        pedido.refresh_from_db()
        messages.warning(
            request,
            'Este retiro fue cancelado automaticamente porque pasaron mas de 24 hs desde la confirmacion.',
        )
    return render(request, 'pedidos/detalle_pedido_proveedor.html', _contexto_detalle_pedido(pedido))


@login_required(login_url='login')
@require_POST
def gestionar_pedido(request, pk):
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')
    pedido = get_object_or_404(Pedido, pk=pk, proveedor=proveedor)
    form = GestionarPedidoForm(
        request.POST, solicitud_credito=pedido.forma_pago == 'solicitud_credito',
    )
    if not form.is_valid():
        return render(request, 'pedidos/detalle_pedido_proveedor.html', _contexto_detalle_pedido(pedido, form))
    accion = form.cleaned_data['accion']
    respuesta = (form.cleaned_data['respuesta'] or '').strip()
    try:
        if accion == 'aceptar':
            aceptar_pedido(
                pedido=pedido, respuesta=respuesta,
                limite_credito=form.cleaned_data.get('limite_credito'),
            )
            mensaje = f'Pedido #{pedido.id} aceptado. El técnico fue notificado.'
        else:
            rechazar_pedido(
                pedido=pedido,
                respuesta=respuesta,
                alternativa=accion == 'alternativa',
            )
            mensaje = (
                f'Alternativa enviada al técnico para el pedido #{pedido.id}.'
                if accion == 'alternativa'
                else f'Pedido #{pedido.id} rechazado. El técnico fue notificado.'
            )
    except EstadoPedidoInvalido:
        messages.error(request, 'Solo podés gestionar pedidos en estado pendiente.')
        return redirect('detalle_pedido_proveedor', pk=pk)
    except (SaldoInsuficiente, LimiteCreditoInvalido) as error:
        mensaje = (
            'El límite debe cubrir la deuda actual más el importe de este pedido. '
            'Revisá el cupo antes de aprobar.'
            if isinstance(error, SaldoInsuficiente) else str(error)
        )
        form.add_error('limite_credito', mensaje)
        return render(request, 'pedidos/detalle_pedido_proveedor.html', _contexto_detalle_pedido(pedido, form))
    except StockInsuficiente as error:
        messages.error(request, str(error))
        return redirect('detalle_pedido_proveedor', pk=pk)
    messages.success(request, mensaje)
    return redirect('pedidos_recibidos')


@login_required(login_url='login')
@require_POST
def completar_pedido(request, pk):
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')
    pedido = get_object_or_404(Pedido, pk=pk, tecnico=tecnico)
    cancelar_retiros_vencidos([pedido])
    try:
        completar_pedido_servicio(pedido=pedido)
    except EstadoPedidoInvalido:
        messages.error(request, 'Solo podés confirmar la recepción de pedidos en estado aceptado.')
    else:
        messages.success(
            request,
            f'Pedido #{pedido.id} marcado como completado. ¡Ya podés calificar a {pedido.proveedor.nombre_negocio}!',
        )
    return redirect('mis_pedidos')
