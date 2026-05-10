from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import (
    RegistroTecnicoForm, RegistroProveedorForm, LoginForm,
    EditarPerfilTecnicoForm, EditarPerfilProveedorForm,
)
from .models import Tecnico, Proveedor


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
    """Vista para la página de aterrizaje (Landing Page)"""
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
    tecnico = get_object_or_404(Tecnico, pk=pk, estado='aprobado', usuario__is_active=True)
    return render(request, 'plataforma/perfil_tecnico.html', {'tecnico': tecnico})


@login_required(login_url='login')
def perfil_proveedor(request, pk):
    """Perfil público de un proveedor, visible para técnicos"""
    proveedor = get_object_or_404(Proveedor, pk=pk, estado='aprobado', usuario__is_active=True)
    return render(request, 'plataforma/perfil_proveedor.html', {'proveedor': proveedor})


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
