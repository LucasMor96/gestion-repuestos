from dataclasses import dataclass

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction


@dataclass(frozen=True)
class ResultadoAutenticacion:
    usuario: User | None
    estado: str
    mensaje: str = ''


def autenticar_por_email(*, email, password):
    usuario = User.objects.filter(email=email).first()
    if usuario is None or not usuario.check_password(password):
        return ResultadoAutenticacion(None, 'credenciales_invalidas')
    if not usuario.is_active:
        perfil = getattr(usuario, 'tecnico', None) or getattr(usuario, 'proveedor', None)
        estado = perfil.estado if perfil else 'pendiente'
        nota = perfil.nota_admin if perfil else ''
        mensajes = {
            'rechazado': 'Tu solicitud fue rechazada.',
            'suspendido': 'Tu cuenta ha sido suspendida.',
        }
        mensaje = mensajes.get(
            estado, 'Tu cuenta está pendiente de aprobación por el administrador.'
        )
        if nota and estado in mensajes:
            mensaje += f' Motivo: {nota}'
        return ResultadoAutenticacion(usuario, estado, mensaje)
    autenticado = authenticate(username=usuario.username, password=password)
    if autenticado is None:
        return ResultadoAutenticacion(None, 'credenciales_invalidas')
    return ResultadoAutenticacion(autenticado, 'aprobado')


@transaction.atomic
def cambiar_estado_perfil(*, perfil, estado, nota=''):
    perfil = type(perfil).objects.select_for_update().select_related('usuario').get(pk=perfil.pk)
    perfil.estado = estado
    perfil.is_approved = estado == 'aprobado'
    perfil.nota_admin = '' if estado == 'aprobado' else nota
    perfil.save(update_fields=['estado', 'is_approved', 'nota_admin'])
    perfil.usuario.is_active = estado == 'aprobado'
    perfil.usuario.save(update_fields=['is_active'])
    return perfil


@transaction.atomic
def guardar_nota_moderacion(*, perfil, nota=''):
    perfil = type(perfil).objects.select_for_update().get(pk=perfil.pk)
    perfil.nota_admin = nota
    perfil.save(update_fields=['nota_admin'])
    return perfil
