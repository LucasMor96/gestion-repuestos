from datetime import timedelta

from django.db import models
from django.utils import timezone

from .tecnico import Tecnico
from .proveedor import Proveedor
from .producto import Producto


class Pedido(models.Model):
    """Pedido de repuesto entre técnico y proveedor (US-07, US-08, US-09)"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aceptado', 'Aceptado'),
        ('rechazado', 'Rechazado'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]

    ENTREGA_CHOICES = [
        ('retiro', 'Retiro en local'),
        ('envio', 'Envío'),
    ]

    FORMA_PAGO_CHOICES = [
        ('mercadopago', 'MercadoPago (simulado)'),
        ('transferencia', 'Transferencia bancaria'),
        ('credito_comercial', 'Credito comercial'),
    ]

    tecnico = models.ForeignKey(Tecnico, on_delete=models.CASCADE, related_name='pedidos')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='pedidos_recibidos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='pedidos')
    cantidad = models.IntegerField()
    forma_entrega = models.CharField(max_length=10, choices=ENTREGA_CHOICES)
    forma_pago = models.CharField(max_length=25, choices=FORMA_PAGO_CHOICES, default='transferencia')
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    notas = models.TextField(blank=True, null=True)
    respuesta_proveedor = models.TextField(blank=True, null=True)
    comprobante_transferencia = models.FileField(upload_to='comprobantes_transferencia/', blank=True, null=True)
    usa_credito = models.BooleanField(default=False)

    @property
    def fecha_limite_retiro(self):
        if self.forma_entrega != 'retiro' or self.estado != 'aceptado':
            return None
        return self.fecha_actualizacion + timedelta(hours=24)

    @property
    def retiro_vencido(self):
        limite = self.fecha_limite_retiro
        return limite is not None and timezone.now() > limite

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Pedido {self.id} - {self.tecnico} a {self.proveedor}"
