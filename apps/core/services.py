from django.db.models import Count, Sum

from apps.pedidos.models import Pedido


def formatear_tiempo_respuesta(promedio_segundos):
    if promedio_segundos is None:
        return 'Sin respuestas'
    if promedio_segundos < 3600:
        return f'{max(1, round(promedio_segundos / 60))} min'
    if promedio_segundos < 86400:
        return f'{round(promedio_segundos / 3600, 1)} h'
    return f'{round(promedio_segundos / 86400, 1)} dias'


def _promedio_respuesta(pedidos):
    tiempos = [
        (pedido.fecha_actualizacion - pedido.fecha_creacion).total_seconds()
        for pedido in pedidos
        if pedido.estado != 'pendiente' and pedido.fecha_actualizacion and pedido.fecha_creacion
    ]
    return sum(tiempos) / len(tiempos) if tiempos else None


def estadisticas_dashboard(*, perfil, es_tecnico, es_proveedor):
    pedidos = Pedido.objects.con_relaciones()
    if es_tecnico:
        pedidos = pedidos.filter(tecnico=perfil)
    elif es_proveedor:
        pedidos = pedidos.filter(proveedor=perfil)
    else:
        pedidos = pedidos.none()
    completados = pedidos.filter(estado='completado')
    totales = completados.aggregate(
        ventas_total=Sum('monto_total'),
        unidades_vendidas=Sum('cantidad'),
    )
    return {
        'total_pedidos': pedidos.count(),
        'ventas_total': totales['ventas_total'] or 0,
        'unidades_vendidas': totales['unidades_vendidas'] or 0,
        'tiempo_respuesta': formatear_tiempo_respuesta(_promedio_respuesta(pedidos)),
        'productos_mas_pedidos': pedidos.values('producto__nombre').annotate(
            cantidad_total=Sum('cantidad'), pedidos_total=Count('id')
        ).order_by('-cantidad_total', 'producto__nombre')[:5],
    }
