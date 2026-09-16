from django.db import models

from apps.usuarios.models import Proveedor, Tecnico


class CreditoQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(activo=True)

    def para_tecnico(self, tecnico):
        return self.select_related('proveedor').filter(tecnico=tecnico)

    def para_proveedor(self, proveedor):
        return self.select_related('tecnico__usuario').filter(proveedor=proveedor)

    def con_deuda(self):
        return self.filter(saldo_usado__gt=0).order_by('-saldo_usado')


class Credito(models.Model):
    """Límite de crédito entre proveedor y técnico (US-10, US-11, US-12)"""
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='creditos')
    tecnico = models.ForeignKey(Tecnico, on_delete=models.CASCADE, related_name='creditos')
    limite = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_usado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ciclo = models.PositiveIntegerField(default=0, editable=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    objects = CreditoQuerySet.as_manager()

    @property
    def saldo_disponible(self):
        return self.limite - self.saldo_usado

    @property
    def porcentaje_usado(self):
        if self.limite == 0:
            return 100
        return int((self.saldo_usado / self.limite) * 100)

    class Meta:
        verbose_name = "Crédito"
        verbose_name_plural = "Créditos"
        unique_together = ('proveedor', 'tecnico')

    def __str__(self):
        return f"Crédito {self.tecnico.usuario.username} con {self.proveedor.nombre_negocio}"

    @property
    def pago_pendiente(self):
        pagos_prefetched = getattr(self, 'pagos_pendientes', None)
        if pagos_prefetched is not None:
            return next((pago for pago in pagos_prefetched if pago.ciclo == self.ciclo), None)
        return self.pagos.filter(ciclo=self.ciclo, estado='pendiente').first()


class PagoCredito(models.Model):
    """Solicitud de pago de una deuda de crédito, confirmable por el proveedor."""

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de confirmación'),
        ('confirmado', 'Confirmado'),
        ('rechazado', 'Rechazado'),
    ]

    credito = models.ForeignKey(Credito, on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    ciclo = models.PositiveIntegerField()
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'Pago {self.monto} de {self.credito.tecnico.usuario.username}'
