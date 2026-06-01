from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import (
    EditarPerfilProveedorForm,
    EditarPerfilTecnicoForm,
    LoginForm,
    RegistroProveedorForm,
    RegistroTecnicoForm,
)
from ..models import Proveedor, Tecnico


def registro_tipo(request):
    """Vista para elegir tipo de registro: tÃ©cnico o proveedor."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    return render(request, 'plataforma/registro_tipo.html')


def registro_tecnico(request):
    """Registro de tÃ©cnico."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistroTecnicoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registro exitoso. Espera la aprobaciÃ³n del administrador para poder ingresar.')
            return redirect('espera_aprobacion')
    else:
        form = RegistroTecnicoForm()
    return render(request, 'plataforma/registro_tecnico.html', {'form': form})


def registro_proveedor(request):
    """Registro de proveedor."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistroProveedorForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registro exitoso. Espera la aprobaciÃ³n del administrador para poder ingresar.')
            return redirect('espera_aprobacion')
    else:
        form = RegistroProveedorForm()
    return render(request, 'plataforma/registro_proveedor.html', {'form': form})


def login_view(request):
    """Login con email."""
    if request.user.is_authenticated:
        return redirect('dashboard')

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
                            messages.warning(request, 'Tu cuenta estÃ¡ pendiente de aprobaciÃ³n por el administrador.')
                        return redirect('espera_aprobacion')

                    login(request, user_obj)
                    messages.success(request, f'Bienvenido, {user_obj.first_name}!')
                    return redirect('dashboard')
                messages.error(request, 'Email o contraseÃ±a incorrectos.')
            except User.DoesNotExist:
                messages.error(request, 'Email o contraseÃ±a incorrectos.')
    else:
        form = LoginForm()
    return render(request, 'plataforma/login.html', {'form': form})


def logout_view(request):
    """Cerrar sesiÃ³n."""
    logout(request)
    messages.success(request, 'SesiÃ³n cerrada correctamente.')
    return redirect('login')


@login_required(login_url='login')
def dashboard(request):
    """Dashboard - vista con acceso restringido."""
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
    """Vista que muestra mensaje de espera / resultado de moderaciÃ³n."""
    return render(request, 'plataforma/espera_aprobacion.html')


def inicio(request):
    """Landing page, redirige al dashboard si ya estÃ¡ autenticado."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'plataforma/inicio.html')


@login_required(login_url='login')
def editar_perfil(request):
    """Permite al usuario editar su propio perfil."""
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
    """Perfil pÃºblico de un tÃ©cnico, visible para proveedores."""
    tecnico = get_object_or_404(Tecnico, pk=pk)
    return render(request, 'plataforma/perfil_tecnico.html', {
        'tecnico': tecnico,
        'es_proveedor': hasattr(request.user, 'proveedor'),
    })


@login_required(login_url='login')
def perfil_proveedor(request, pk):
    """Perfil pÃºblico de un proveedor, visible para tÃ©cnicos."""
    proveedor = get_object_or_404(Proveedor, pk=pk)
    articulos_vendidos = (
        proveedor.pedidos_recibidos
        .filter(estado='completado')
        .aggregate(total=Sum('cantidad'))['total'] or 0
    )
    return render(request, 'plataforma/perfil_proveedor.html', {
        'proveedor': proveedor,
        'articulos_vendidos': articulos_vendidos,
    })
