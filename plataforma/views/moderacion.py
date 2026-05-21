from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..models import Proveedor, Tecnico
from .utils import solo_staff


@login_required(login_url='login')
def panel_moderacion(request):
    """Panel de moderaciÃ³n de usuarios (solo staff)."""
    if not solo_staff(request):
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
    """Aprueba el registro de un tÃ©cnico o proveedor."""
    if not solo_staff(request):
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
    """Rechaza el registro de un tÃ©cnico o proveedor."""
    if not solo_staff(request):
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
    """Suspende una cuenta activa."""
    if not solo_staff(request):
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
    """Solicita informaciÃ³n adicional a un usuario pendiente."""
    if not solo_staff(request):
        return redirect('dashboard')

    if request.method == 'POST':
        perfil = get_object_or_404(Tecnico if tipo == 'tecnico' else Proveedor, pk=pk)
        perfil.nota_admin = request.POST.get('nota', '')
        perfil.save()
        messages.success(request, f'Nota guardada para {perfil.usuario.get_full_name()}. El usuario la verÃ¡ al intentar ingresar.')
    return redirect('panel_moderacion')
