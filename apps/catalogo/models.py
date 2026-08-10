from django.db import models

from apps.usuarios.choices import RUBROS_CHOICES
from apps.usuarios.models import Proveedor


class ProductoQuerySet(models.QuerySet):
    def publicados(self):
        return self.filter(disponible=True)

    def del_proveedor(self, proveedor):
        return self.filter(proveedor=proveedor)

    def buscar(self, *, texto='', categoria='', orden=''):
        from django.db.models import Q, Sum

        queryset = self.publicados().select_related('proveedor').annotate(
            unidades_vendidas=Sum(
                'pedidos__cantidad',
                filter=Q(pedidos__estado='completado'),
                default=0,
            )
        )
        if texto:
            queryset = queryset.filter(
                Q(nombre__icontains=texto)
                | Q(modelo__icontains=texto)
                | Q(categoria__icontains=texto)
            )
        if categoria:
            queryset = queryset.filter(categoria__icontains=categoria)
        ordenes = {
            'precio_asc': 'precio',
            'precio_desc': '-precio',
            'mas_vendidos': '-unidades_vendidas',
        }
        if orden in ordenes:
            queryset = queryset.order_by(ordenes[orden], 'nombre')
        return queryset


class Producto(models.Model):
    """Catálogo de productos del proveedor (US-06)"""
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name="productos")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    modelo = models.CharField(max_length=100, blank=True)
    categoria = models.CharField(max_length=100, choices=RUBROS_CHOICES)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    disponible = models.BooleanField(default=True)

    objects = ProductoQuerySet.as_manager()

    def alternar_disponibilidad(self):
        self.disponible = not self.disponible
        self.save(update_fields=['disponible'])
        return self.disponible

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.nombre} ({self.proveedor.nombre_negocio})"
