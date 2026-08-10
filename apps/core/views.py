from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import redirect, render

from apps.catalogo.models import Producto
from apps.pedidos.models import Pedido
from apps.usuarios.utils import perfil_aprobado


def _formatear_tiempo_respuesta(promedio_segundos):
    if promedio_segundos is None:
        return 'Sin respuestas'
    if promedio_segundos < 3600:
        minutos = max(1, round(promedio_segundos / 60))
        return f'{minutos} min'
    if promedio_segundos < 86400:
        horas = round(promedio_segundos / 3600, 1)
        return f'{horas} h'
    dias = round(promedio_segundos / 86400, 1)
    return f'{dias} dias'

def _promedio_respuesta(pedidos):
    tiempos = [
        (pedido.fecha_actualizacion - pedido.fecha_creacion).total_seconds()
        for pedido in pedidos
        if pedido.estado != 'pendiente' and pedido.fecha_actualizacion and pedido.fecha_creacion
    ]
    if not tiempos:
        return None
    return sum(tiempos) / len(tiempos)

def _estadisticas_dashboard(perfil, es_tecnico, es_proveedor):
    pedidos_personales = Pedido.objects.select_related('producto', 'proveedor', 'tecnico')
    if es_tecnico:
        pedidos_personales = pedidos_personales.filter(tecnico=perfil)
    elif es_proveedor:
        pedidos_personales = pedidos_personales.filter(proveedor=perfil)
    else:
        pedidos_personales = pedidos_personales.none()

    pedidos_completados = pedidos_personales.filter(estado='completado')
    total_pedidos = pedidos_personales.count()
    ventas_total = pedidos_completados.aggregate(total=Sum('monto_total'))['total'] or 0
    unidades_vendidas = pedidos_completados.aggregate(total=Sum('cantidad'))['total'] or 0

    productos_mas_pedidos = (
        pedidos_personales
        .values('producto__nombre')
        .annotate(cantidad_total=Sum('cantidad'), pedidos_total=Count('id'))
        .order_by('-cantidad_total', 'producto__nombre')[:5]
    )

    proveedores_con_mas_ventas = (
        Pedido.objects
        .filter(estado='completado')
        .values('proveedor__nombre_negocio')
        .annotate(ventas_total=Sum('monto_total'), cantidad_total=Sum('cantidad'), pedidos_total=Count('id'))
        .order_by('-ventas_total', 'proveedor__nombre_negocio')[:5]
    )

    return {
        'total_pedidos': total_pedidos,
        'ventas_total': ventas_total,
        'unidades_vendidas': unidades_vendidas,
        'tiempo_respuesta': _formatear_tiempo_respuesta(_promedio_respuesta(pedidos_personales)),
        'productos_mas_pedidos': productos_mas_pedidos,
        'proveedores_con_mas_ventas': proveedores_con_mas_ventas,
    }

@login_required(login_url='login')
def dashboard(request):
    """Dashboard - vista con acceso restringido."""
    if not request.user.is_active:
        return redirect('espera_aprobacion')
    if request.user.is_staff:
        return redirect('panel_moderacion')

    context = {
        'es_tecnico': hasattr(request.user, 'tecnico'),
        'es_proveedor': hasattr(request.user, 'proveedor'),
    }
    if context['es_tecnico']:
        context['perfil'] = request.user.tecnico
        if not perfil_aprobado(context['perfil']):
            return redirect('espera_aprobacion')
    elif context['es_proveedor']:
        context['perfil'] = request.user.proveedor
        if not perfil_aprobado(context['perfil']):
            return redirect('espera_aprobacion')
    else:
        return redirect('espera_aprobacion')

    if 'perfil' in context:
        context['estadisticas'] = _estadisticas_dashboard(
            context['perfil'],
            context['es_tecnico'],
            context['es_proveedor'],
        )

    return render(request, 'core/dashboard.html', context)

def inicio(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    productos_destacados = Producto.objects.all().order_by('-id')[:5]

    print("PRODUCTOS:", productos_destacados.count())
    for p in productos_destacados:
        print(p.id, p.nombre)

    return render(request, 'core/inicio.html', {
        'productos_destacados': productos_destacados
    })
