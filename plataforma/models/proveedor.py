from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg

from .choices import RUBROS_CHOICES, ESTADO_USUARIO_CHOICES


class Proveedor(models.Model):
    """Perfil de negocio proveedor de repuestos (US-03)"""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    cuit = models.CharField(max_length=13, unique=True, null=True, blank=True)
    nombre_negocio = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255)
    rubro = models.CharField(max_length=100, choices=RUBROS_CHOICES)
    horarios = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to='proveedores/logos/', blank=True, null=True)
    imagen = models.ImageField(upload_to='proveedores/imagenes/', blank=True, null=True)
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_USUARIO_CHOICES, default='pendiente')
    nota_admin = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    email_confirmed = models.BooleanField(default=False)

    @property
    def calificacion_promedio(self):
        calificaciones = self.calificaciones_recibidas.all()
        if not calificaciones.exists():
            return None
        result = calificaciones.aggregate(avg=Avg('estrellas'))
        return round(result['avg'], 1)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"

    def __str__(self):
        return self.nombre_negocio
