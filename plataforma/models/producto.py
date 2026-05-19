from django.db import models

from .choices import RUBROS_CHOICES
from .proveedor import Proveedor


class Producto(models.Model):
    """Catálogo de productos del proveedor (US-06)"""
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name="productos")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    categoria = models.CharField(max_length=100, choices=RUBROS_CHOICES)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    disponible = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.nombre} ({self.proveedor.nombre_negocio})"
