from datetime import timedelta

from django.db import models
from django.db.models import Exists, OuterRef, Q

from apps.catalogo.models import Producto
from apps.usuarios.models import Proveedor, Tecnico


class PedidoQuerySet(models.QuerySet):
    def con_relaciones(self):
        return self.select_related(
            'producto', 'producto_alternativo', 'proveedor', 'tecnico__usuario',
        )

    def para_historial(self, *, tecnico, fecha_desde='', fecha_hasta='', proveedor_id=''):
        from apps.calificaciones.models import CalificacionProveedor

        queryset = self.con_relaciones().filter(tecnico=tecnico).annotate(
            ya_calificado=Exists(CalificacionProveedor.objects.filter(pedido=OuterRef('pk')))
        )
        if fecha_desde:
            queryset = queryset.filter(fecha_creacion__date__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_creacion__date__lte=fecha_hasta)
        if proveedor_id:
            queryset = queryset.filter(proveedor_id=proveedor_id)
        return queryset.order_by('-fecha_creacion')

    def recibidos_por(self, proveedor):
        from apps.calificaciones.models import CalificacionTecnico

        return self.con_relaciones().filter(proveedor=proveedor).annotate(
            ya_calificado=Exists(CalificacionTecnico.objects.filter(pedido=OuterRef('pk')))
        )

    def deuda_credito(self, *, proveedor, tecnico):
        return self.filter(
            Q(usa_credito=True) | Q(forma_pago='credito_comercial'),
            proveedor=proveedor,
            tecnico=tecnico,
        ).exclude(estado__in=['cancelado', 'rechazado']).order_by('-fecha_creacion')


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
        ('transferencia', 'Transferencia bancaria'),
        ('credito_comercial', 'Credito comercial'),
        ('solicitud_credito', 'Solicitud de crédito'),
    ]

    tecnico = models.ForeignKey(Tecnico, on_delete=models.CASCADE, related_name='pedidos')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='pedidos_recibidos')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='pedidos')
    producto_alternativo = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='pedidos_como_alternativa',
        blank=True,
        null=True,
    )
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
    ciclo_credito = models.PositiveIntegerField(default=0, editable=False)
    clave_operacion = models.UUIDField(null=True, blank=True, editable=False)

    objects = PedidoQuerySet.as_manager()

    def get_forma_pago_display(self):
        # Conserva los pedidos históricos sin ofrecer nuevamente el medio retirado.
        return dict(self.FORMA_PAGO_CHOICES).get(self.forma_pago, 'Medio de pago retirado (histórico)')

    @property
    def fecha_limite_retiro(self):
        if self.forma_entrega != 'retiro' or self.estado != 'aceptado':
            return None
        return self.fecha_actualizacion + timedelta(hours=24)

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_creacion']
        constraints = [
            models.UniqueConstraint(
                fields=['tecnico', 'producto', 'clave_operacion'],
                name='pedido_operacion_unica',
            ),
        ]

    def __str__(self):
        return f"Pedido {self.id} - {self.tecnico} a {self.proveedor}"
