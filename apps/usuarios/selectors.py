from django.contrib.auth.models import User
from django.db.models import Sum
from django.db.models.functions import Lower, Trim

from .models import Proveedor, Tecnico
from .utils import normalizar_email


def usuarios_por_email(email):
    return User.objects.exclude(email='').alias(
        email_normalizado=Lower(Trim('email')),
    ).filter(email_normalizado=normalizar_email(email))


def contexto_moderacion():
    return {
        'tecnicos_pendientes': Tecnico.objects.filter(estado='pendiente').select_related('usuario').prefetch_related('usuario__respuestas_moderacion__imagenes'),
        'proveedores_pendientes': Proveedor.objects.filter(estado='pendiente').select_related('usuario').prefetch_related('usuario__respuestas_moderacion__imagenes'),
        'tecnicos_activos': Tecnico.objects.filter(estado='aprobado').select_related('usuario').prefetch_related('usuario__respuestas_moderacion__imagenes'),
        'proveedores_activos': Proveedor.objects.filter(estado='aprobado').select_related('usuario').prefetch_related('usuario__respuestas_moderacion__imagenes'),
        'tecnicos_inactivos': Tecnico.objects.filter(estado__in=['rechazado', 'suspendido']).select_related('usuario').prefetch_related('usuario__respuestas_moderacion__imagenes'),
        'proveedores_inactivos': Proveedor.objects.filter(estado__in=['rechazado', 'suspendido']).select_related('usuario').prefetch_related('usuario__respuestas_moderacion__imagenes'),
    }


def articulos_vendidos_proveedor(proveedor):
    return proveedor.pedidos_recibidos.filter(estado='completado').aggregate(
        total=Sum('cantidad')
    )['total'] or 0
