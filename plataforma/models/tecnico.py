from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg

from .choices import RUBROS_CHOICES, ESTADO_USUARIO_CHOICES


class Tecnico(models.Model):
    """Perfil profesional de técnico independiente (US-02)"""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    cuit = models.CharField(max_length=13, unique=True, null=True, blank=True)
    especialidad = models.CharField(max_length=100, choices=RUBROS_CHOICES)
    telefono = models.CharField(max_length=20, blank=True)
    ubicacion = models.CharField(max_length=200)
    estado = models.CharField(max_length=15, choices=ESTADO_USUARIO_CHOICES, default='pendiente')
    nota_admin = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)

    @property
    def calificacion_promedio(self):
        calificaciones = self.calificaciones_recibidas.all()
        if not calificaciones.exists():
            return None
        result = calificaciones.aggregate(avg_p=Avg('puntualidad'), avg_t=Avg('trato'))
        return round((result['avg_p'] + result['avg_t']) / 2, 1)

    class Meta:
        verbose_name = "Técnico"
        verbose_name_plural = "Técnicos"

    def __str__(self):
        return f"Técnico: {self.usuario.username} - {self.especialidad}"
