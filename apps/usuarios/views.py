from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    EditarPerfilProveedorForm,
    EditarPerfilTecnicoForm,
    LoginForm,
    RegistroProveedorForm,
    RegistroTecnicoForm,
)
from .models import Proveedor, Tecnico
from .selectors import articulos_vendidos_proveedor
from .services import autenticar_por_email
from .utils import get_proveedor_o_403, get_tecnico_o_403, perfil_aprobado


def registro_tipo(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'usuarios/registro_tipo.html')


def registro_tecnico(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegistroTecnicoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request,
            'Registro exitoso. Espera la aprobación del administrador para poder ingresar.',
        )
        return redirect('espera_aprobacion')
    return render(request, 'usuarios/registro_tecnico.html', {'form': form})


def registro_proveedor(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegistroProveedorForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request,
            'Registro exitoso. Espera la aprobación del administrador para poder ingresar.',
        )
        return redirect('espera_aprobacion')
    return render(request, 'usuarios/registro_proveedor.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        resultado = autenticar_por_email(**form.cleaned_data)
        if resultado.estado == 'aprobado':
            login(request, resultado.usuario)
            messages.success(request, f'Bienvenido, {resultado.usuario.first_name}!')
            return redirect('dashboard')
        if resultado.estado == 'rechazado':
            messages.error(request, resultado.mensaje)
            return redirect('espera_aprobacion')
        if resultado.estado in {'suspendido', 'pendiente'}:
            messages.warning(request, resultado.mensaje)
            return redirect('espera_aprobacion')
        messages.error(request, 'Email o contraseña incorrectos.')
    return render(request, 'usuarios/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'Sesión cerrada correctamente.')
    return redirect('login')


def espera_aprobacion(request):
    return render(request, 'usuarios/espera_aprobacion.html')


@login_required(login_url='login')
def editar_perfil(request):
    if not request.user.is_active:
        return redirect('espera_aprobacion')
    if hasattr(request.user, 'tecnico'):
        perfil = request.user.tecnico
        formulario = EditarPerfilTecnicoForm
        archivos = None
    elif hasattr(request.user, 'proveedor'):
        perfil = request.user.proveedor
        formulario = EditarPerfilProveedorForm
        archivos = request.FILES or None
    else:
        return redirect('dashboard')
    if not perfil_aprobado(perfil):
        return redirect('espera_aprobacion')
    form = formulario(
        request.POST or None,
        archivos,
        instance=perfil,
        user=request.user,
    ) if archivos is not None or formulario is EditarPerfilProveedorForm else formulario(
        request.POST or None, instance=perfil, user=request.user
    )
    if request.method == 'POST' and form.is_valid():
        form.save_user(request.user)
        form.save()
        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('dashboard')
    return render(request, 'usuarios/editar_perfil.html', {'form': form})


@login_required(login_url='login')
def perfil_tecnico(request, pk):
    if get_proveedor_o_403(request) is None:
        return redirect('dashboard')
    tecnico = get_object_or_404(
        Tecnico, pk=pk, estado='aprobado', is_approved=True, usuario__is_active=True
    )
    return render(request, 'usuarios/perfil_tecnico.html', {
        'tecnico': tecnico,
        'es_proveedor': hasattr(request.user, 'proveedor'),
    })


@login_required(login_url='login')
def perfil_proveedor(request, pk):
    if get_tecnico_o_403(request) is None:
        return redirect('dashboard')
    proveedor = get_object_or_404(
        Proveedor, pk=pk, estado='aprobado', is_approved=True, usuario__is_active=True
    )
    return render(request, 'usuarios/perfil_proveedor.html', {
        'proveedor': proveedor,
        'articulos_vendidos': articulos_vendidos_proveedor(proveedor),
    })
