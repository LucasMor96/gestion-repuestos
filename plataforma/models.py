from django.db import models
from django.contrib.auth.models import User

# Perfil del Técnico (Basado en US-02 y DER)
class Tecnico(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    rubro = models.CharField(max_length=100)  # Cambiado de especialidad a rubro
    ubicacion = models.CharField(max_length=200)

    def __str__(self):
        return f"Técnico: {self.usuario.username} - {self.rubro}"

# Perfil del Proveedor (Basado en US-03 y DER)
class Proveedor(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    nombre_negocio = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255)
    rubro = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre_negocio

# Catálogo de Productos (Basado en US-06 y DER)
class Producto(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)
    categoria = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.proveedor.nombre_negocio})"

# Gestión de Créditos (Basado en US-11 y DER)
class Credito(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)
    tecnico = models.ForeignKey(Tecnico, on_delete=models.CASCADE)
    limite = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_usado = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Crédito de {self.tecnico} con {self.proveedor}"