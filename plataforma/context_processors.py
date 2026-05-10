def pedidos_pendientes(request):
    """Inyecta el conteo de pedidos pendientes para proveedores en todos los templates."""
    count = 0
    if request.user.is_authenticated and hasattr(request.user, 'proveedor'):
        count = request.user.proveedor.pedidos_recibidos.filter(estado='pendiente').count()
    return {'pedidos_pendientes_count': count}
