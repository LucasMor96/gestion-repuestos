import csv
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..forms import GestionarPedidoForm, PedidoForm
from ..models import CalificacionProveedor, CalificacionTecnico, Credito, Pedido, Producto, Proveedor
from .notifications import (
    notificar_alerta_credito,
    notificar_pedido_confirmado,
    notificar_proveedor_nuevo_pedido,
    notificar_tecnico_estado,
)
from .utils import get_proveedor_o_403, get_tecnico_o_403


def cancelar_retiros_vencidos(pedidos):
    """Cancela retiros aceptados que superaron las 24 hs sin confirmacion."""
    cutoff = timezone.now() - timedelta(hours=24)
    vencidos = [
        pedido for pedido in pedidos
        if pedido.estado == 'aceptado'
        and pedido.forma_entrega == 'retiro'
        and pedido.fecha_actualizacion <= cutoff
    ]

    for pedido in vencidos:
        pedido.estado = 'cancelado'
        pedido.respuesta_proveedor = 'Compra cancelada automaticamente: no se retiro dentro de las 24 hs posteriores a la confirmacion.'
        pedido.save()

        producto = pedido.producto
        producto.stock += pedido.cantidad
        producto.save()

        if pedido.usa_credito:
            try:
                credito = Credito.objects.get(proveedor=pedido.proveedor, tecnico=pedido.tecnico)
                credito.saldo_usado = max(0, credito.saldo_usado - pedido.monto_total)
                credito.save()
            except Credito.DoesNotExist:
                pass

    return len(vencidos)


def agregar_datos_envio_a_notas(pedido, cleaned_data):
    if cleaned_data.get('forma_entrega') != 'envio':
        return

    franja = dict(PedidoForm.base_fields['franja_horaria'].choices).get(cleaned_data.get('franja_horaria'), '')
    datos_envio = (
        'Datos de envio:\n'
        f'- Direccion: {cleaned_data.get("direccion_envio")}\n'
        f'- Telefono: {cleaned_data.get("telefono_contacto")}\n'
        f'- Franja horaria: {franja}'
    )
    notas = (pedido.notas or '').strip()
    pedido.notas = f'{notas}\n\n{datos_envio}' if notas else datos_envio


def calcular_costo_envio(forma_entrega, cantidad):
    if forma_entrega != 'envio':
        return Decimal('0')
    return Decimal('3500') + (Decimal(max(cantidad - 1, 0)) * Decimal('900'))


@login_required(login_url='login')
def crear_pedido(request, producto_pk):
    """Técnico envía una solicitud de compra de un repuesto al proveedor."""
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')

    producto = get_object_or_404(Producto, pk=producto_pk, disponible=True)
    proveedor = producto.proveedor

    try:
        credito = Credito.objects.get(proveedor=proveedor, tecnico=tecnico, activo=True)
    except Credito.DoesNotExist:
        credito = None

    if request.method == 'POST':
        form = PedidoForm(request.POST, stock=producto.stock, tecnico=tecnico)
        if form.is_valid():
            try:
                pedido = form.save(commit=False)
                pedido.tecnico = tecnico
                pedido.proveedor = proveedor
                pedido.producto = producto
                cantidad = form.cleaned_data['cantidad']
                pedido.monto_total = (producto.precio * cantidad) + calcular_costo_envio(
                    form.cleaned_data['forma_entrega'],
                    cantidad,
                )
                pedido.estado = 'pendiente'
                agregar_datos_envio_a_notas(pedido, form.cleaned_data)

                usa_credito = request.POST.get('usa_credito') == 'on' and credito is not None
                if usa_credito:
                    if pedido.monto_total > credito.saldo_disponible:
                        messages.error(
                            request,
                            f'El monto del pedido (${pedido.monto_total}) supera tu crédito disponible '
                            f'(${credito.saldo_disponible}) con {proveedor.nombre_negocio}.'
                        )
                        return render(request, 'plataforma/crear_pedido.html', {
                            'form': form, 'producto': producto, 'credito': credito,
                        })
                    pedido.usa_credito = True
                    pedido.save()
                    credito.saldo_usado += pedido.monto_total
                    credito.save()
                    if credito.porcentaje_usado >= 80:
                        notificar_alerta_credito(credito)
                else:
                    pedido.save()

                notificar_proveedor_nuevo_pedido(pedido)
                messages.success(
                    request,
                    f'Pedido #{pedido.id} enviado correctamente. '
                    f'{proveedor.nombre_negocio} recibirá tu solicitud.'
                )
                return redirect('mis_pedidos')
            except Exception:
                messages.error(request, 'Ocurrió un error al procesar el pedido. Intentá de nuevo.')
    else:
        form = PedidoForm(stock=producto.stock, tecnico=tecnico)

    return render(request, 'plataforma/crear_pedido.html', {'form': form, 'producto': producto, 'credito': credito})


@login_required(login_url='login')
def mis_pedidos(request):
    """Historial de pedidos del técnico con filtros por fecha y proveedor."""
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')

    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()
    proveedor_id = request.GET.get('proveedor', '').strip()

    try:
        cancelar_retiros_vencidos(tecnico.pedidos.select_related('producto', 'proveedor'))

        pedidos_qs = (
            tecnico.pedidos
            .select_related('producto', 'proveedor')
            .annotate(ya_calificado=Exists(CalificacionProveedor.objects.filter(pedido=OuterRef('pk'))))
        )

        if fecha_desde:
            pedidos_qs = pedidos_qs.filter(fecha_creacion__date__gte=fecha_desde)
        if fecha_hasta:
            pedidos_qs = pedidos_qs.filter(fecha_creacion__date__lte=fecha_hasta)
        if proveedor_id:
            pedidos_qs = pedidos_qs.filter(proveedor_id=proveedor_id)

        pedidos = pedidos_qs.order_by('-fecha_creacion')
        proveedores = Proveedor.objects.filter(pedidos_recibidos__tecnico=tecnico).distinct().order_by('nombre_negocio')
        hay_filtros = bool(fecha_desde or fecha_hasta or proveedor_id)

    except Exception:
        messages.error(request, 'Ocurrió un error al cargar tu historial de pedidos. Intentá de nuevo.')
        pedidos = []
        proveedores = []
        hay_filtros = False
        fecha_desde = fecha_hasta = proveedor_id = ''

    return render(request, 'plataforma/mis_pedidos.html', {
        'pedidos': pedidos,
        'proveedores': proveedores,
        'hay_filtros': hay_filtros,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'proveedor_id_sel': proveedor_id,
    })


@login_required(login_url='login')
def exportar_historial(request):
    """Descarga el historial de pedidos del técnico como CSV."""
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')

    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()
    proveedor_id = request.GET.get('proveedor', '').strip()

    try:
        pedidos_qs = tecnico.pedidos.select_related('producto', 'proveedor')

        if fecha_desde:
            pedidos_qs = pedidos_qs.filter(fecha_creacion__date__gte=fecha_desde)
        if fecha_hasta:
            pedidos_qs = pedidos_qs.filter(fecha_creacion__date__lte=fecha_hasta)
        if proveedor_id:
            pedidos_qs = pedidos_qs.filter(proveedor_id=proveedor_id)

        pedidos = pedidos_qs.order_by('-fecha_creacion')

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="historial_pedidos.csv"'
        response.write('\ufeff')  # BOM para compatibilidad con Excel

        writer = csv.writer(response)
        writer.writerow(['#', 'Producto', 'Proveedor', 'Cantidad', 'Entrega', 'Monto ($)', 'Estado', 'Fecha'])

        for pedido in pedidos:
            writer.writerow([
                pedido.id,
                pedido.producto.nombre,
                pedido.proveedor.nombre_negocio,
                pedido.cantidad,
                pedido.get_forma_entrega_display(),
                pedido.monto_total,
                pedido.get_estado_display(),
                pedido.fecha_creacion.strftime('%d/%m/%Y'),
            ])

        return response

    except Exception:
        messages.error(request, 'No se pudo generar el archivo de exportación. Intentá de nuevo.')
        return redirect('mis_pedidos')


@login_required(login_url='login')
@require_POST
def cancelar_pedido(request, pk):
    """Técnico cancela un pedido en estado pendiente."""
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')

    pedido = get_object_or_404(Pedido, pk=pk, tecnico=tecnico)

    if request.method == 'POST':
        if pedido.estado != 'pendiente':
            messages.error(request, 'Solo podés cancelar pedidos en estado pendiente.')
        else:
            pedido.estado = 'cancelado'
            pedido.save()
            if pedido.usa_credito:
                try:
                    credito = Credito.objects.get(proveedor=pedido.proveedor, tecnico=tecnico)
                    credito.saldo_usado = max(0, credito.saldo_usado - pedido.monto_total)
                    credito.save()
                except Credito.DoesNotExist:
                    pass
            messages.success(request, f'Pedido #{pedido.id} cancelado correctamente.')

    return redirect('mis_pedidos')


@login_required(login_url='login')
def pedidos_recibidos(request):
    """Panel de pedidos recibidos para el proveedor."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    pedidos_base = proveedor.pedidos_recibidos.select_related('producto', 'tecnico', 'proveedor')
    cancelar_retiros_vencidos(pedidos_base)

    pedidos = (
        proveedor.pedidos_recibidos
        .select_related('producto', 'tecnico__usuario')
        .annotate(ya_calificado=Exists(CalificacionTecnico.objects.filter(pedido=OuterRef('pk'))))
        .all()
    )
    return render(request, 'plataforma/pedidos_recibidos.html', {'pedidos': pedidos})


@login_required(login_url='login')
def detalle_pedido_proveedor(request, pk):
    """Detalle de un pedido recibido, con información del técnico y formulario de gestión."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    pedido = get_object_or_404(
        Pedido.objects.select_related('producto', 'tecnico__usuario'),
        pk=pk,
        proveedor=proveedor,
    )
    cancelar_retiros_vencidos([pedido])
    if pedido.estado == 'cancelado':
        messages.warning(request, 'Este retiro fue cancelado automaticamente porque pasaron mas de 24 hs desde la confirmacion.')
    form = GestionarPedidoForm()
    return render(request, 'plataforma/detalle_pedido_proveedor.html', {
        'pedido': pedido,
        'form': form,
        'ya_calificado': pedido.calificacion_tecnico.exists(),
    })


@login_required(login_url='login')
def gestionar_pedido(request, pk):
    """Proveedor acepta, rechaza o propone alternativa para un pedido pendiente."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    pedido = get_object_or_404(Pedido, pk=pk, proveedor=proveedor)

    if request.method != 'POST':
        return redirect('detalle_pedido_proveedor', pk=pk)

    if pedido.estado != 'pendiente':
        messages.error(request, 'Solo podés gestionar pedidos en estado pendiente.')
        return redirect('detalle_pedido_proveedor', pk=pk)

    form = GestionarPedidoForm(request.POST)
    if not form.is_valid():
        for error in form.non_field_errors():
            messages.error(request, error)
        return redirect('detalle_pedido_proveedor', pk=pk)

    accion = form.cleaned_data['accion']
    respuesta = (form.cleaned_data['respuesta'] or '').strip()

    try:
        if accion == 'aceptar':
            producto = pedido.producto
            if producto.stock < pedido.cantidad:
                messages.error(
                    request,
                    f'Stock insuficiente. Disponible: {producto.stock}, solicitado: {pedido.cantidad}.'
                )
                return redirect('detalle_pedido_proveedor', pk=pk)
            pedido.estado = 'aceptado'
            pedido.respuesta_proveedor = respuesta or None
            pedido.save()
            producto.stock -= pedido.cantidad
            producto.save()
            notificar_tecnico_estado(pedido)
            messages.success(request, f'Pedido #{pedido.id} aceptado. El técnico fue notificado.')

        elif accion == 'rechazar':
            pedido.estado = 'rechazado'
            pedido.respuesta_proveedor = respuesta or None
            pedido.save()
            notificar_tecnico_estado(pedido)
            if pedido.usa_credito:
                try:
                    credito = Credito.objects.get(proveedor=proveedor, tecnico=pedido.tecnico)
                    credito.saldo_usado = max(0, credito.saldo_usado - pedido.monto_total)
                    credito.save()
                except Credito.DoesNotExist:
                    pass
            messages.success(request, f'Pedido #{pedido.id} rechazado. El técnico fue notificado.')

        elif accion == 'alternativa':
            pedido.estado = 'rechazado'
            pedido.respuesta_proveedor = f'Alternativa propuesta: {respuesta}'
            pedido.save()
            notificar_tecnico_estado(pedido)
            if pedido.usa_credito:
                try:
                    credito = Credito.objects.get(proveedor=proveedor, tecnico=pedido.tecnico)
                    credito.saldo_usado = max(0, credito.saldo_usado - pedido.monto_total)
                    credito.save()
                except Credito.DoesNotExist:
                    pass
            messages.success(
                request,
                f'Alternativa enviada al técnico para el pedido #{pedido.id}.'
            )

    except Exception:
        messages.error(request, 'Ocurrió un error al procesar la acción. Intentá de nuevo.')
        return redirect('detalle_pedido_proveedor', pk=pk)

    return redirect('pedidos_recibidos')


@login_required(login_url='login')
@require_POST
def completar_pedido(request, pk):
    """Técnico marca un pedido aceptado como completado (recibió el repuesto)."""
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')

    pedido = get_object_or_404(Pedido, pk=pk, tecnico=tecnico)
    cancelar_retiros_vencidos([pedido])

    if request.method == 'POST':
        if pedido.estado != 'aceptado':
            messages.error(request, 'Solo podés confirmar la recepción de pedidos en estado aceptado.')
        else:
            pedido.estado = 'completado'
            pedido.save()
            notificar_pedido_confirmado(pedido)
            messages.success(
                request,
                f'Pedido #{pedido.id} marcado como completado. ¡Ya podés calificar a {pedido.proveedor.nombre_negocio}!'
            )

    return redirect('mis_pedidos')
