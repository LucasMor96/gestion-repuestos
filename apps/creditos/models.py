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
