from django.contrib.auth.models import User
from django.db import models
from django.db.models import Avg

from .choices import ESTADO_USUARIO_CHOICES, RUBROS_CHOICES
from .storage import almacenamiento_moderacion, ruta_imagen_moderacion


class RespuestaModeracion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='respuestas_moderacion')
    solicitud = models.TextField()
    texto = models.TextField(blank=True)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creada', '-pk']


class ImagenModeracion(models.Model):
    respuesta = models.ForeignKey(RespuestaModeracion, on_delete=models.CASCADE, related_name='imagenes')
    extension = models.CharField(max_length=5)
    imagen = models.ImageField(storage=almacenamiento_moderacion, upload_to=ruta_imagen_moderacion)


class Tecnico(models.Model):
    """Perfil profesional de técnico independiente (US-02)."""

    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    cuit = models.CharField(max_length=13, unique=True, null=True, blank=True)
    especialidad = models.CharField(max_length=100, choices=RUBROS_CHOICES)
    telefono = models.CharField(max_length=20, blank=True)
    ubicacion = models.CharField(max_length=200)
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
        result = calificaciones.aggregate(avg_p=Avg('puntualidad'), avg_t=Avg('trato'))
        return round((result['avg_p'] + result['avg_t']) / 2, 1)

    class Meta:
        verbose_name = 'Técnico'
        verbose_name_plural = 'Técnicos'

    def __str__(self):
        return f'Técnico: {self.usuario.username} - {self.especialidad}'


class Proveedor(models.Model):
    """Perfil de negocio proveedor de repuestos (US-03)."""

    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    cuit = models.CharField(max_length=13, unique=True, null=True, blank=True)
    nombre_negocio = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255)
    rubro = models.CharField(max_length=100, choices=RUBROS_CHOICES)
    horarios = models.CharField(max_length=200, blank=True)
    banco_transferencia = models.CharField(max_length=100, blank=True)
    titular_transferencia = models.CharField(max_length=150, blank=True)
    cbu_transferencia = models.CharField(max_length=30, blank=True)
    alias_transferencia = models.CharField(max_length=50, blank=True)
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
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return self.nombre_negocio
