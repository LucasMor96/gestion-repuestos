from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import signing
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    EditarPerfilProveedorForm,
    EditarPerfilTecnicoForm,
    LoginForm,
    RegistroProveedorForm,
    RegistroTecnicoForm,
    RespuestaModeracionForm,
)
from .models import ImagenModeracion, Proveedor, RespuestaModeracion, Tecnico
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
        request.session.pop('acceso_moderacion', None)
        resultado = autenticar_por_email(**form.cleaned_data)
        if resultado.usuario and resultado.estado != 'aprobado':
            request.session.cycle_key()
            request.session['acceso_moderacion'] = signing.dumps({
                'usuario': resultado.usuario.pk,
                'hash': resultado.usuario.get_session_auth_hash(),
            }, salt='moderacion')
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


def password_recovery(request):
    return render(request, 'usuarios/password_recovery.html')


def usuario_moderacion(request):
    if request.user.is_authenticated:
        return request.user
    try:
        datos = signing.loads(request.session.get('acceso_moderacion', ''),
                              salt='moderacion', max_age=3600)
        usuario = User.objects.get(pk=datos['usuario'])
        if datos['hash'] == usuario.get_session_auth_hash():
            return usuario
    except (signing.BadSignature, User.DoesNotExist, KeyError):
        pass
    return None


def espera_aprobacion(request):
    usuario = usuario_moderacion(request)
    perfil = (getattr(usuario, 'tecnico', None) or getattr(usuario, 'proveedor', None)) if usuario else None
    form = None
    if perfil and perfil.estado == 'pendiente' and perfil.nota_admin:
        form = RespuestaModeracionForm(request.POST if request.method == 'POST' else None, request.FILES)
        if request.method == 'POST' and form.is_valid():
            with transaction.atomic():
                perfil = type(perfil).objects.select_for_update().get(pk=perfil.pk)
                if perfil.estado != 'pendiente' or not perfil.nota_admin:
                    return redirect('espera_aprobacion')
                respuesta = RespuestaModeracion.objects.create(
                    usuario=usuario, solicitud=perfil.nota_admin, texto=form.cleaned_data['texto'])
                for archivo in form.cleaned_data['imagenes']:
                    extension = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}[archivo.image.format]
                    ImagenModeracion.objects.create(respuesta=respuesta, imagen=archivo, extension=extension)
            messages.success(request, 'Información enviada. El administrador revisará tu respuesta.')
            return redirect('espera_aprobacion')
    elif request.method == 'POST':
        return redirect('login')
    return render(request, 'usuarios/espera_aprobacion.html', {
        'perfil': perfil, 'form': form,
        'respuestas': usuario.respuestas_moderacion.prefetch_related('imagenes').all() if usuario else [],
    })


def imagen_moderacion(request, pk):
    usuario = usuario_moderacion(request)
    if usuario is None:
        raise Http404
    imagen = get_object_or_404(ImagenModeracion.objects.select_related('respuesta'), pk=pk)
    if not (usuario.is_active and usuario.is_staff) and imagen.respuesta.usuario_id != usuario.pk:
        raise Http404
    try:
        archivo = imagen.imagen.open('rb')
    except FileNotFoundError:
        raise Http404
    response = FileResponse(archivo, content_type={'.jpg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}[imagen.extension])
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


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
