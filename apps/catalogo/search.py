from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.usuarios.utils import get_tecnico_o_403

from .selectors import buscar_productos, categorias_publicadas


@login_required(login_url='login')
def buscar_repuestos(request):
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')
    query = request.GET.get('q', '').strip()
    categoria_sel = request.GET.get('categoria', '').strip()
    orden = request.GET.get('orden', '')
    return render(request, 'catalogo/buscar_repuestos.html', {
        'productos': list(buscar_productos(
            texto=query, categoria=categoria_sel, orden=orden
        )),
        'query': query,
        'categoria_sel': categoria_sel,
        'orden': orden,
        'categorias': categorias_publicadas(),
        'es_tecnico': hasattr(request.user, 'tecnico'),
    })
