from django.db import models

from pedidos.models import Pedido
from usuarios.models import Proveedor, Tecnico


ESTRELLAS_CHOICES = [(i, f"{i} estrella{'s' if i != 1 else ''}") for i in range(1, 6)]


class CalificacionProveedor(models.Model):
    """Calificación de proveedor por técnico (US-13)"""
    tecnico = models.ForeignKey(Tecnico, on_delete=models.CASCADE, related_name='calificaciones_dadas')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='calificaciones_recibidas')
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='calificacion_proveedor')
    estrellas = models.IntegerField(choices=ESTRELLAS_CHOICES)
    comentario = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Calificación Proveedor"
        verbose_name_plural = "Calificaciones Proveedores"
        unique_together = ('tecnico', 'pedido')
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.tecnico.usuario.username} → {self.proveedor.nombre_negocio} ({self.estrellas}⭐)"

    def save(self, *args, **kwargs):
        if self.pedido.estado != 'completado':
            raise ValueError("Solo se pueden calificar pedidos completados")
        super().save(*args, **kwargs)


class CalificacionTecnico(models.Model):
    """Calificación de técnico por proveedor (US-14)"""
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='calificaciones_dadas')
    tecnico = models.ForeignKey(Tecnico, on_delete=models.CASCADE, related_name='calificaciones_recibidas')
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='calificacion_tecnico')
    puntualidad = models.IntegerField(choices=ESTRELLAS_CHOICES)
    trato = models.IntegerField(choices=ESTRELLAS_CHOICES)
    comentario_privado = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Calificación Técnico"
        verbose_name_plural = "Calificaciones Técnicos"
        unique_together = ('proveedor', 'pedido')
        ordering = ['-fecha_creacion']

    def __str__(self):
        promedio = (self.puntualidad + self.trato) / 2
        return f"{self.proveedor.nombre_negocio} → {self.tecnico.usuario.username} ({promedio:.1f}⭐)"

    def save(self, *args, **kwargs):
        if self.pedido.estado != 'completado':
            raise ValueError("Solo se pueden calificar pedidos completados")
        super().save(*args, **kwargs)
