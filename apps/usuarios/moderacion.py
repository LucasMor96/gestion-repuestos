from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Proveedor, Tecnico
from .selectors import contexto_moderacion
from .services import cambiar_estado_perfil, guardar_nota_moderacion
from .utils import solo_staff


def get_perfil_moderacion(tipo, pk):
    if tipo == 'tecnico':
        modelo = Tecnico
    elif tipo == 'proveedor':
        modelo = Proveedor
    else:
        raise Http404('Tipo de usuario invalido.')

    return get_object_or_404(modelo, pk=pk)


@login_required(login_url='login')
def panel_moderacion(request):
    """Panel de moderacion de usuarios (solo staff)."""
    if not solo_staff(request):
        return redirect('dashboard')

    context = contexto_moderacion()
    return render(request, 'usuarios/panel_moderacion.html', context)


@login_required(login_url='login')
@require_POST
def aprobar_usuario(request, tipo, pk):
    """Aprueba el registro de un tecnico o proveedor."""
    if not solo_staff(request):
        return redirect('dashboard')

    perfil = get_perfil_moderacion(tipo, pk)
    perfil = cambiar_estado_perfil(perfil=perfil, estado='aprobado')
    messages.success(request, f'{perfil.usuario.get_full_name()} fue aprobado/a correctamente.')
    return redirect('panel_moderacion')


@login_required(login_url='login')
@require_POST
def rechazar_usuario(request, tipo, pk):
    """Rechaza el registro de un tecnico o proveedor."""
    if not solo_staff(request):
        return redirect('dashboard')

    perfil = get_perfil_moderacion(tipo, pk)
    perfil = cambiar_estado_perfil(
        perfil=perfil, estado='rechazado', nota=request.POST.get('nota', '')
    )
    messages.success(request, f'Solicitud de {perfil.usuario.get_full_name()} rechazada.')
    return redirect('panel_moderacion')


@login_required(login_url='login')
@require_POST
def suspender_usuario(request, tipo, pk):
    """Suspende una cuenta activa."""
    if not solo_staff(request):
        return redirect('dashboard')

    perfil = get_perfil_moderacion(tipo, pk)
    perfil = cambiar_estado_perfil(
        perfil=perfil, estado='suspendido', nota=request.POST.get('nota', '')
    )
    messages.success(request, f'Cuenta de {perfil.usuario.get_full_name()} suspendida.')
    return redirect('panel_moderacion')


@login_required(login_url='login')
@require_POST
def solicitar_info(request, tipo, pk):
    """Solicita informacion adicional a un usuario pendiente."""
    if not solo_staff(request):
        return redirect('dashboard')

    perfil = get_perfil_moderacion(tipo, pk)
    nota = request.POST.get('nota', '').strip()
    if perfil.estado != 'pendiente' or not nota:
        messages.error(request, 'Indicá la información requerida para una cuenta pendiente.')
        return redirect('panel_moderacion')
    perfil = guardar_nota_moderacion(perfil=perfil, nota=nota)
    messages.success(request, f'Nota guardada para {perfil.usuario.get_full_name()}.')
    return redirect('panel_moderacion')
