from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import RegistroTecnicoForm, RegistroProveedorForm, LoginForm
from .models import Tecnico, Proveedor


def registro_tipo(request):
    """Vista para elegir tipo de registro: técnico o proveedor"""
    return render(request, 'plataforma/registro_tipo.html')


def registro_tecnico(request):
    """Registro de técnico"""
    if request.method == 'POST':
        form = RegistroTecnicoForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registro exitoso. Espera la aprobación del administrador para poder ingresar.')
            return redirect('espera_aprobacion')
    else:
        form = RegistroTecnicoForm()

    return render(request, 'plataforma/registro_tecnico.html', {'form': form})


def registro_proveedor(request):
    """Registro de proveedor"""
    if request.method == 'POST':
        form = RegistroProveedorForm(request.POST)
        if form.is_valid():
            user = form.save()
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
    """Vista que muestra mensaje de espera de aprobación"""
    return render(request, 'plataforma/espera_aprobacion.html')
