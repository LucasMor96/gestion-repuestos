from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from ..models import Producto
from .utils import haversine


@login_required(login_url='login')
def buscar_repuestos(request):
    """Búsqueda de repuestos por nombre, modelo o categoría (US-04)."""
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

            for producto in productos_lista:
                proveedor = producto.proveedor
                if proveedor.latitud is not None and proveedor.longitud is not None:
                    producto.distancia_km = round(
                        haversine(user_lat, user_lng, proveedor.latitud, proveedor.longitud),
                        1,
                    )
                else:
                    producto.distancia_km = None

            productos_lista.sort(
                key=lambda producto: producto.distancia_km
                if producto.distancia_km is not None
                else float('inf')
            )

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
