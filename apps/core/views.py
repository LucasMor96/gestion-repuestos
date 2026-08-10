from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.catalogo.models import Producto
from apps.usuarios.utils import perfil_aprobado

from .services import estadisticas_dashboard


@login_required(login_url='login')
def dashboard(request):
    if not request.user.is_active:
        return redirect('espera_aprobacion')
    if request.user.is_staff:
        return redirect('panel_moderacion')
    es_tecnico = hasattr(request.user, 'tecnico')
    es_proveedor = hasattr(request.user, 'proveedor')
    perfil = request.user.tecnico if es_tecnico else request.user.proveedor if es_proveedor else None
    if perfil is None or not perfil_aprobado(perfil):
        return redirect('espera_aprobacion')
    return render(request, 'core/dashboard.html', {
        'es_tecnico': es_tecnico,
        'es_proveedor': es_proveedor,
        'perfil': perfil,
        'estadisticas': estadisticas_dashboard(
            perfil=perfil, es_tecnico=es_tecnico, es_proveedor=es_proveedor
        ),
    })


def inicio(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/inicio.html', {
        'productos_destacados': Producto.objects.order_by('-id')[:5],
    })
