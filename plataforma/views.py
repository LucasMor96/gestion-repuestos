from math import radians, sin, cos, sqrt, atan2

from django.db.models import Q, Exists, OuterRef, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail

from .forms import (
    RegistroTecnicoForm, RegistroProveedorForm, LoginForm,
    EditarPerfilTecnicoForm, EditarPerfilProveedorForm,
    ProductoForm, PedidoForm, GestionarPedidoForm,
    AsignarCreditoForm,
    CalificacionProveedorForm, CalificacionTecnicoForm,
)
from .models import Tecnico, Proveedor, Producto, Pedido, Credito, CalificacionProveedor, CalificacionTecnico


def _solo_staff(request):
    if not request.user.is_staff:
        messages.error(request, 'No tenés permisos para acceder a esta sección.')
        return False
    return True


def registro_tipo(request):
    """Vista para elegir tipo de registro: técnico o proveedor"""
    return render(request, 'plataforma/registro_tipo.html')


def registro_tecnico(request):
    """Registro de técnico"""
    if request.method == 'POST':
        form = RegistroTecnicoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registro exitoso. Espera la aprobación del administrador para poder ingresar.')
            return redirect('espera_aprobacion')
    else:
        form = RegistroTecnicoForm()
    return render(request, 'plataforma/registro_tecnico.html', {'form': form})


def registro_proveedor(request):
    """Registro de proveedor"""
    if request.method == 'POST':
        form = RegistroProveedorForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registro exitoso. Espera la aprobación del administrador para poder ingresar.')
            return redirect('espera_aprobacion')
    else:
        form = RegistroProveedorForm()
    return render(request, 'plataforma/registro_proveedor.html', {'form': form})


def login_view(request):
    """Login con email"""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = User.objects.get(email=email)
                user_obj = authenticate(request, username=user.username, password=password)
                if user_obj is not None:
                    if not user_obj.is_active:
                        perfil = None
                        if hasattr(user_obj, 'tecnico'):
                            perfil = user_obj.tecnico
                        elif hasattr(user_obj, 'proveedor'):
                            perfil = user_obj.proveedor

                        estado = perfil.estado if perfil else 'pendiente'
                        nota = perfil.nota_admin if perfil else ''

                        if estado == 'rechazado':
                            msg = 'Tu solicitud fue rechazada.'
                            if nota:
                                msg += f' Motivo: {nota}'
                            messages.error(request, msg)
                        elif estado == 'suspendido':
                            msg = 'Tu cuenta ha sido suspendida.'
                            if nota:
                                msg += f' Motivo: {nota}'
                            messages.warning(request, msg)
                        else:
                            messages.warning(request, 'Tu cuenta está pendiente de aprobación por el administrador.')
                        return redirect('espera_aprobacion')

                    login(request, user_obj)
                    messages.success(request, f'Bienvenido, {user_obj.first_name}!')
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Email o contraseña incorrectos.')
            except User.DoesNotExist:
                messages.error(request, 'Email o contraseña incorrectos.')
    else:
        form = LoginForm()
    return render(request, 'plataforma/login.html', {'form': form})


def logout_view(request):
    """Cerrar sesión"""
    logout(request)
    messages.success(request, 'Sesión cerrada correctamente.')
    return redirect('login')


@login_required(login_url='login')
def dashboard(request):
    """Dashboard - vista con acceso restringido"""
    if not request.user.is_active:
        return redirect('espera_aprobacion')

    context = {
        'es_tecnico': hasattr(request.user, 'tecnico'),
        'es_proveedor': hasattr(request.user, 'proveedor'),
    }
    if context['es_tecnico']:
        context['perfil'] = request.user.tecnico
    elif context['es_proveedor']:
        context['perfil'] = request.user.proveedor

    return render(request, 'plataforma/dashboard.html', context)


def espera_aprobacion(request):
    """Vista que muestra mensaje de espera / resultado de moderación"""
    return render(request, 'plataforma/espera_aprobacion.html')


def inicio(request):
    """Landing page — redirige al dashboard si ya está autenticado."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'plataforma/inicio.html')


@login_required(login_url='login')
def editar_perfil(request):
    """Permite al usuario editar su propio perfil"""
    if hasattr(request.user, 'tecnico'):
        perfil = request.user.tecnico
        if request.method == 'POST':
            form = EditarPerfilTecnicoForm(request.POST, instance=perfil, user=request.user)
            if form.is_valid():
                form.save_user(request.user)
                form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
                return redirect('dashboard')
        else:
            form = EditarPerfilTecnicoForm(instance=perfil, user=request.user)

    elif hasattr(request.user, 'proveedor'):
        perfil = request.user.proveedor
        if request.method == 'POST':
            form = EditarPerfilProveedorForm(request.POST, request.FILES, instance=perfil, user=request.user)
            if form.is_valid():
                form.save_user(request.user)
                form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
                return redirect('dashboard')
        else:
            form = EditarPerfilProveedorForm(instance=perfil, user=request.user)
    else:
        return redirect('dashboard')

    return render(request, 'plataforma/editar_perfil.html', {'form': form})


@login_required(login_url='login')
def perfil_tecnico(request, pk):
    """Perfil público de un técnico, visible para proveedores"""
    tecnico = get_object_or_404(Tecnico, pk=pk)
    return render(request, 'plataforma/perfil_tecnico.html', {
        'tecnico': tecnico,
        'es_proveedor': hasattr(request.user, 'proveedor'),
    })


@login_required(login_url='login')
def perfil_proveedor(request, pk):
    """Perfil público de un proveedor, visible para técnicos"""
    proveedor = get_object_or_404(Proveedor, pk=pk)
    articulos_vendidos = (
        proveedor.pedidos_recibidos
        .filter(estado='completado')
        .aggregate(total=Sum('cantidad'))['total'] or 0
    )
    return render(request, 'plataforma/perfil_proveedor.html', {
        'proveedor': proveedor,
        'articulos_vendidos': articulos_vendidos,
    })


@login_required(login_url='login')
def panel_moderacion(request):
    """Panel de moderación de usuarios (solo staff)"""
    if not _solo_staff(request):
        return redirect('dashboard')

    context = {
        'tecnicos_pendientes': Tecnico.objects.filter(estado='pendiente').select_related('usuario'),
        'proveedores_pendientes': Proveedor.objects.filter(estado='pendiente').select_related('usuario'),
        'tecnicos_activos': Tecnico.objects.filter(estado='aprobado').select_related('usuario'),
        'proveedores_activos': Proveedor.objects.filter(estado='aprobado').select_related('usuario'),
        'tecnicos_inactivos': Tecnico.objects.filter(estado__in=['rechazado', 'suspendido']).select_related('usuario'),
        'proveedores_inactivos': Proveedor.objects.filter(estado__in=['rechazado', 'suspendido']).select_related('usuario'),
    }
    return render(request, 'plataforma/panel_moderacion.html', context)


@login_required(login_url='login')
def aprobar_usuario(request, tipo, pk):
    """Aprueba el registro de un técnico o proveedor"""
    if not _solo_staff(request):
        return redirect('dashboard')

    perfil = get_object_or_404(Tecnico if tipo == 'tecnico' else Proveedor, pk=pk)
    perfil.estado = 'aprobado'
    perfil.is_approved = True
    perfil.nota_admin = ''
    perfil.save()
    perfil.usuario.is_active = True
    perfil.usuario.save()
    messages.success(request, f'{perfil.usuario.get_full_name()} fue aprobado/a correctamente.')
    return redirect('panel_moderacion')


@login_required(login_url='login')
def rechazar_usuario(request, tipo, pk):
    """Rechaza el registro de un técnico o proveedor"""
    if not _solo_staff(request):
        return redirect('dashboard')

    if request.method == 'POST':
        perfil = get_object_or_404(Tecnico if tipo == 'tecnico' else Proveedor, pk=pk)
        perfil.estado = 'rechazado'
        perfil.is_approved = False
        perfil.nota_admin = request.POST.get('nota', '')
        perfil.save()
        perfil.usuario.is_active = False
        perfil.usuario.save()
        messages.success(request, f'Solicitud de {perfil.usuario.get_full_name()} rechazada.')
    return redirect('panel_moderacion')


@login_required(login_url='login')
def suspender_usuario(request, tipo, pk):
    """Suspende una cuenta activa"""
    if not _solo_staff(request):
        return redirect('dashboard')

    if request.method == 'POST':
        perfil = get_object_or_404(Tecnico if tipo == 'tecnico' else Proveedor, pk=pk)
        perfil.estado = 'suspendido'
        perfil.nota_admin = request.POST.get('nota', '')
        perfil.save()
        perfil.usuario.is_active = False
        perfil.usuario.save()
        messages.success(request, f'Cuenta de {perfil.usuario.get_full_name()} suspendida.')
    return redirect('panel_moderacion')


@login_required(login_url='login')
def solicitar_info(request, tipo, pk):
    """Solicita información adicional a un usuario pendiente"""
    if not _solo_staff(request):
        return redirect('dashboard')

    if request.method == 'POST':
        perfil = get_object_or_404(Tecnico if tipo == 'tecnico' else Proveedor, pk=pk)
        perfil.nota_admin = request.POST.get('nota', '')
        perfil.save()
        messages.success(request, f'Nota guardada para {perfil.usuario.get_full_name()}. El usuario la verá al intentar ingresar.')
    return redirect('panel_moderacion')


def _haversine(lat1, lon1, lat2, lon2):
    """Distancia en km entre dos coordenadas (fórmula de Haversine)."""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


@login_required(login_url='login')
def buscar_repuestos(request):
    """Búsqueda de repuestos por nombre, modelo o categoría (US-04)"""
    query = request.GET.get('q', '').strip()
    categoria_sel = request.GET.get('categoria', '').strip()
    orden = request.GET.get('orden', '')
    lat_str = request.GET.get('lat', '')
    lng_str = request.GET.get('lng', '')

    try:
        productos = Producto.objects.filter(disponible=True).select_related('proveedor')

        if query:
            productos = productos.filter(
                Q(nombre__icontains=query) |
                Q(modelo__icontains=query) |
                Q(categoria__icontains=query)
            )

        if categoria_sel:
            productos = productos.filter(categoria__icontains=categoria_sel)

        if orden == 'precio_asc':
            productos = productos.order_by('precio')
        elif orden == 'precio_desc':
            productos = productos.order_by('-precio')

        categorias = (
            Producto.objects
            .filter(disponible=True)
            .values_list('categoria', flat=True)
            .distinct()
            .order_by('categoria')
        )

        productos_lista = list(productos)

        if orden == 'distancia' and lat_str and lng_str:
            user_lat = float(lat_str)
            user_lng = float(lng_str)

            for p in productos_lista:
                prov = p.proveedor
                if prov.latitud is not None and prov.longitud is not None:
                    p.distancia_km = round(_haversine(user_lat, user_lng, prov.latitud, prov.longitud), 1)
                else:
                    p.distancia_km = None

            productos_lista.sort(key=lambda p: p.distancia_km if p.distancia_km is not None else float('inf'))

        context = {
            'productos': productos_lista,
            'query': query,
            'categoria_sel': categoria_sel,
            'orden': orden,
            'categorias': categorias,
            'lat': lat_str,
            'lng': lng_str,
            'es_tecnico': hasattr(request.user, 'tecnico'),
        }
    except Exception:
        messages.error(request, 'Ocurrió un error al realizar la búsqueda. Intentá de nuevo.')
        context = {
            'productos': [],
            'query': query,
            'categoria_sel': categoria_sel,
            'orden': orden,
            'categorias': [],
            'lat': lat_str,
            'lng': lng_str,
            'es_tecnico': hasattr(request.user, 'tecnico'),
        }

    return render(request, 'plataforma/buscar_repuestos.html', context)


# ---------------------------------------------------------------------------
# Catálogo de productos – US-06 (solo proveedores)
# ---------------------------------------------------------------------------

def _get_proveedor_o_403(request):
    """Devuelve el perfil Proveedor del usuario o None si no corresponde."""
    if not hasattr(request.user, 'proveedor'):
        messages.error(request, 'Esta sección es solo para proveedores.')
        return None
    return request.user.proveedor


def _get_tecnico_o_403(request):
    """Devuelve el perfil Tecnico del usuario o None si no corresponde."""
    if not hasattr(request.user, 'tecnico'):
        messages.error(request, 'Esta sección es solo para técnicos.')
        return None
    return request.user.tecnico


@login_required(login_url='login')
def catalogo_proveedor(request):
    """Lista los productos propios del proveedor."""
    proveedor = _get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    productos = proveedor.productos.all().order_by('nombre')
    return render(request, 'plataforma/catalogo_proveedor.html', {'productos': productos})


@login_required(login_url='login')
def agregar_producto(request):
    """Crea un nuevo producto en el catálogo."""
    proveedor = _get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.proveedor = proveedor
            producto.save()
            messages.success(request, f'Producto "{producto.nombre}" publicado en el catálogo.')
            return redirect('catalogo_proveedor')
    else:
        form = ProductoForm()

    return render(request, 'plataforma/producto_form.html', {'form': form, 'accion': 'Agregar'})


@login_required(login_url='login')
def editar_producto(request, pk):
    """Edita un producto existente."""
    proveedor = _get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    producto = get_object_or_404(Producto, pk=pk, proveedor=proveedor)

    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, f'Producto "{producto.nombre}" actualizado.')
            return redirect('catalogo_proveedor')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'plataforma/producto_form.html', {'form': form, 'accion': 'Editar', 'producto': producto})


@login_required(login_url='login')
def eliminar_producto(request, pk):
    """Elimina un producto tras confirmación POST."""
    proveedor = _get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    producto = get_object_or_404(Producto, pk=pk, proveedor=proveedor)

    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        messages.success(request, f'Producto "{nombre}" eliminado del catálogo.')
    return redirect('catalogo_proveedor')


@login_required(login_url='login')
def toggle_disponibilidad(request, pk):
    """Activa o desactiva la visibilidad de un producto sin editar el resto."""
    proveedor = _get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    producto = get_object_or_404(Producto, pk=pk, proveedor=proveedor)
    producto.disponible = not producto.disponible
    producto.save(update_fields=['disponible'])
    estado = 'visible' if producto.disponible else 'oculto'
    messages.success(request, f'"{producto.nombre}" ahora está {estado} en el catálogo.')
    return redirect('catalogo_proveedor')


# ---------------------------------------------------------------------------
# Pedidos de repuestos – US-07 / US-08
# ---------------------------------------------------------------------------

def _notificar_proveedor_nuevo_pedido(pedido):
    """Envía email al proveedor cuando llega un nuevo pedido."""
    send_mail(
        subject=f'[Repuestos] Nuevo pedido #{pedido.id} — {pedido.producto.nombre}',
        message=(
            f'Hola {pedido.proveedor.usuario.first_name},\n\n'
            f'Recibiste un nuevo pedido en la plataforma:\n\n'
            f'  Producto : {pedido.producto.nombre}\n'
            f'  Cantidad : {pedido.cantidad}\n'
            f'  Monto    : ${pedido.monto_total}\n'
            f'  Entrega  : {pedido.get_forma_entrega_display()}\n'
            f'  Técnico  : {pedido.tecnico.usuario.get_full_name()}\n'
            f'  Teléfono : {pedido.tecnico.telefono or "No informado"}\n\n'
            f'Ingresá a la plataforma para aceptar o rechazar el pedido.\n'
        ),
        from_email='noreply@gestion-repuestos.com',
        recipient_list=[pedido.proveedor.usuario.email],
        fail_silently=True,
    )


def _notificar_tecnico_estado(pedido):
    """Envía email al técnico cuando el proveedor cambia el estado de su pedido."""
    send_mail(
        subject=f'[Repuestos] Pedido #{pedido.id} — {pedido.get_estado_display()}',
        message=(
            f'Hola {pedido.tecnico.usuario.first_name},\n\n'
            f'Tu pedido fue actualizado:\n\n'
            f'  Producto  : {pedido.producto.nombre}\n'
            f'  Estado    : {pedido.get_estado_display()}\n'
            f'  Proveedor : {pedido.proveedor.nombre_negocio}\n'
            + (f'  Mensaje   : {pedido.respuesta_proveedor}\n' if pedido.respuesta_proveedor else '')
            + '\nIngresá a la plataforma para ver el detalle de tus pedidos.\n'
        ),
        from_email='noreply@gestion-repuestos.com',
        recipient_list=[pedido.tecnico.usuario.email],
        fail_silently=True,
    )


def _notificar_credito_asignado(credito):
    send_mail(
        subject=f'[Repuestos] Crédito comercial asignado — {credito.proveedor.nombre_negocio}',
        message=(
            f'Hola {credito.tecnico.usuario.first_name},\n\n'
            f'{credito.proveedor.nombre_negocio} te asignó un crédito comercial:\n\n'
            f'  Límite disponible: ${credito.limite}\n\n'
            f'Ya podés usarlo al hacer pedidos con este proveedor.\n'
        ),
        from_email='noreply@gestion-repuestos.com',
        recipient_list=[credito.tecnico.usuario.email],
        fail_silently=True,
    )


def _notificar_alerta_credito(credito):
    send_mail(
        subject=f'[Repuestos] Alerta: límite de crédito con {credito.proveedor.nombre_negocio}',
        message=(
            f'Hola {credito.tecnico.usuario.first_name},\n\n'
            f'Usaste el {credito.porcentaje_usado}% de tu crédito con {credito.proveedor.nombre_negocio}:\n\n'
            f'  Límite total    : ${credito.limite}\n'
            f'  Saldo usado     : ${credito.saldo_usado}\n'
            f'  Saldo disponible: ${credito.saldo_disponible}\n\n'
            f'Por favor, regularizá tu deuda para seguir usando el crédito.\n'
        ),
        from_email='noreply@gestion-repuestos.com',
        recipient_list=[credito.tecnico.usuario.email],
        fail_silently=True,
    )


def _notificar_deuda_saldada(credito):
    send_mail(
        subject=f'[Repuestos] Tu deuda con {credito.proveedor.nombre_negocio} fue saldada',
        message=(
            f'Hola {credito.tecnico.usuario.first_name},\n\n'
            f'{credito.proveedor.nombre_negocio} marcó tu deuda como saldada.\n\n'
            f'Tu crédito disponible se restableció. Límite: ${credito.limite}\n'
        ),
        from_email='noreply@gestion-repuestos.com',
        recipient_list=[credito.tecnico.usuario.email],
        fail_silently=True,
    )


def _notificar_credito_revocado(credito):
    send_mail(
        subject=f'[Repuestos] Tu crédito con {credito.proveedor.nombre_negocio} fue revocado',
        message=(
            f'Hola {credito.tecnico.usuario.first_name},\n\n'
            f'{credito.proveedor.nombre_negocio} revocó tu crédito comercial.\n\n'
            f'Si tenés saldo pendiente, contactá al proveedor para regularizar tu situación.\n'
        ),
        from_email='noreply@gestion-repuestos.com',
        recipient_list=[credito.tecnico.usuario.email],
        fail_silently=True,
    )


@login_required(login_url='login')
def crear_pedido(request, producto_pk):
    """Técnico envía una solicitud de compra de un repuesto al proveedor."""
    tecnico = _get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('buscar_repuestos')

    producto = get_object_or_404(Producto, pk=producto_pk, disponible=True)
    proveedor = producto.proveedor

    try:
        credito = Credito.objects.get(proveedor=proveedor, tecnico=tecnico, activo=True)
    except Credito.DoesNotExist:
        credito = None

    if request.method == 'POST':
        form = PedidoForm(request.POST, stock=producto.stock)
        if form.is_valid():
            try:
                pedido = form.save(commit=False)
                pedido.tecnico = tecnico
                pedido.proveedor = proveedor
                pedido.producto = producto
                pedido.monto_total = producto.precio * form.cleaned_data['cantidad']
                pedido.estado = 'pendiente'

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
                        _notificar_alerta_credito(credito)
                else:
                    pedido.save()

                _notificar_proveedor_nuevo_pedido(pedido)
                messages.success(
                    request,
                    f'Pedido #{pedido.id} enviado correctamente. '
                    f'{proveedor.nombre_negocio} recibirá tu solicitud.'
                )
                return redirect('mis_pedidos')
            except Exception:
                messages.error(request, 'Ocurrió un error al procesar el pedido. Intentá de nuevo.')
    else:
        form = PedidoForm(stock=producto.stock)

    return render(request, 'plataforma/crear_pedido.html', {'form': form, 'producto': producto, 'credito': credito})


@login_required(login_url='login')
def mis_pedidos(request):
    """Historial de pedidos del técnico con filtros por fecha y proveedor."""
    tecnico = _get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')

    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()
    proveedor_id = request.GET.get('proveedor', '').strip()

    try:
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
    import csv
    from django.http import HttpResponse

    tecnico = _get_tecnico_o_403(request)
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
        response.write('﻿')  # BOM para compatibilidad con Excel

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
def cancelar_pedido(request, pk):
    """Técnico cancela un pedido en estado pendiente."""
    tecnico = _get_tecnico_o_403(request)
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
    proveedor = _get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

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
    proveedor = _get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    pedido = get_object_or_404(
        Pedido.objects.select_related('producto', 'tecnico__usuario'),
        pk=pk,
        proveedor=proveedor,
    )
    form = GestionarPedidoForm()
    return render(request, 'plataforma/detalle_pedido_proveedor.html', {
        'pedido': pedido,
        'form': form,
        'ya_calificado': pedido.calificacion_tecnico.exists(),
    })


@login_required(login_url='login')
def gestionar_pedido(request, pk):
    """Proveedor acepta, rechaza o propone alternativa para un pedido pendiente."""
    proveedor = _get_proveedor_o_403(request)
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
            _notificar_tecnico_estado(pedido)
            messages.success(request, f'Pedido #{pedido.id} aceptado. El técnico fue notificado.')

        elif accion == 'rechazar':
            pedido.estado = 'rechazado'
            pedido.respuesta_proveedor = respuesta or None
            pedido.save()
            _notificar_tecnico_estado(pedido)
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
            _notificar_tecnico_estado(pedido)
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


# ---------------------------------------------------------------------------
# Completar pedido – transición aceptado → completado (técnico confirma recepción)
# ---------------------------------------------------------------------------

@login_required(login_url='login')
def completar_pedido(request, pk):
    """Técnico marca un pedido aceptado como completado (recibió el repuesto)."""
    tecnico = _get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')

    pedido = get_object_or_404(Pedido, pk=pk, tecnico=tecnico)

    if request.method == 'POST':
        if pedido.estado != 'aceptado':
            messages.error(request, 'Solo podés confirmar la recepción de pedidos en estado aceptado.')
        else:
            pedido.estado = 'completado'
            pedido.save()
            messages.success(
                request,
                f'Pedido #{pedido.id} marcado como completado. ¡Ya podés calificar a {pedido.proveedor.nombre_negocio}!'
            )

    return redirect('mis_pedidos')


# ---------------------------------------------------------------------------
# Crédito comercial – US-10 / US-11 / US-12
# ---------------------------------------------------------------------------

@login_required(login_url='login')
def mis_creditos(request):
    """Técnico ve sus créditos disponibles con cada proveedor (US-10)."""
    tecnico = _get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')

    creditos = tecnico.creditos.select_related('proveedor').filter(activo=True)
    return render(request, 'plataforma/mis_creditos.html', {'creditos': creditos})


@login_required(login_url='login')
def gestionar_creditos_proveedor(request):
    """Proveedor ve y administra los créditos asignados a técnicos (US-11)."""
    proveedor = _get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    creditos = proveedor.creditos.select_related('tecnico__usuario').filter(activo=True).order_by(
        'tecnico__usuario__last_name'
    )
    return render(request, 'plataforma/gestionar_creditos_proveedor.html', {'creditos': creditos})


@login_required(login_url='login')
def asignar_credito(request):
    """Proveedor asigna o edita el límite de crédito de un técnico (US-11)."""
    proveedor = _get_proveedor_o_403(request)
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
                _notificar_credito_asignado(credito)
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
    proveedor = _get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    credito = get_object_or_404(Credito, pk=pk, proveedor=proveedor)

    if request.method == 'POST':
        try:
            credito.activo = False
            credito.save()
            _notificar_credito_revocado(credito)
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
    proveedor = _get_proveedor_o_403(request)
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
    proveedor = _get_proveedor_o_403(request)
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
    proveedor = _get_proveedor_o_403(request)
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
                _notificar_deuda_saldada(credito)
                messages.success(
                    request,
                    f'Deuda de {credito.tecnico.usuario.get_full_name()} marcada como saldada. '
                    f'El crédito disponible se restableció.'
                )
        except Exception:
            messages.error(request, 'Ocurrió un error al saldar la deuda. Intentá de nuevo.')

    return redirect('deudas_tecnicos')


# ---------------------------------------------------------------------------
# Calificaciones – US-13 y US-14
# ---------------------------------------------------------------------------

@login_required(login_url='login')
def calificar_proveedor(request, pedido_pk):
    """Técnico califica a un proveedor tras un pedido completado (US-13)."""
    tecnico = _get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')

    pedido = get_object_or_404(Pedido, pk=pedido_pk, tecnico=tecnico)

    if pedido.estado != 'completado':
        messages.error(request, 'Solo podés calificar pedidos completados.')
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
                    f'estrella{"s" if estrellas != 1 else ""}. ¡Gracias por tu opinión!'
                )
                return redirect('mis_pedidos')
            except ValueError as e:
                messages.error(request, str(e))
            except Exception:
                messages.error(request, 'Ocurrió un error al guardar la calificación. Intentá de nuevo.')
    else:
        form = CalificacionProveedorForm()

    return render(request, 'plataforma/calificar_proveedor.html', {
        'form': form,
        'pedido': pedido,
    })


@login_required(login_url='login')
def calificar_tecnico(request, pedido_pk):
    """Proveedor califica a un técnico tras un pedido completado (US-14)."""
    proveedor = _get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    pedido = get_object_or_404(Pedido, pk=pedido_pk, proveedor=proveedor)

    if pedido.estado != 'completado':
        messages.error(request, 'Solo podés calificar técnicos con pedidos completados.')
        return redirect('pedidos_recibidos')

    if pedido.calificacion_tecnico.exists():
        messages.warning(request, 'Ya calificaste a este técnico por este pedido.')
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
                    f'Calificaste al técnico {pedido.tecnico.usuario.get_full_name()} correctamente. ¡Gracias!'
                )
                return redirect('pedidos_recibidos')
            except ValueError as e:
                messages.error(request, str(e))
            except Exception:
                messages.error(request, 'Ocurrió un error al guardar la calificación. Intentá de nuevo.')
    else:
        form = CalificacionTecnicoForm()

    return render(request, 'plataforma/calificar_tecnico.html', {
        'form': form,
        'pedido': pedido,
    })
