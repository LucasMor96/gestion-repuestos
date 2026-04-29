from django.db import models
from django.contrib.auth.models import User


class Tecnico(models.Model):
    """Perfil profesional de técnico independiente (US-02)"""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    cuit = models.CharField(max_length=13, unique=True, null=True, blank=True)
    especialidad = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=200)
    is_approved = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Técnico"
        verbose_name_plural = "Técnicos"

    def __str__(self):
        return f"Técnico: {self.usuario.username} - {self.especialidad}"


class Proveedor(models.Model):
    """Perfil de negocio proveedor de repuestos (US-03)"""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    cuit = models.CharField(max_length=13, unique=True, null=True, blank=True)
    nombre_negocio = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255)
    rubro = models.CharField(max_length=100)
    is_approved = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"

    def __str__(self):
        return self.nombre_negocio


class Producto(models.Model):
    """Catálogo de productos del proveedor (US-06)"""
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name="productos")
    nombre = models.CharField(max_length=200)
    categoria = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.nombre} ({self.proveedor.nombre_negocio})"


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

    tecnico = models.ForeignKey(Tecnico, on_delete=models.CASCADE, related_name='pedidos')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='pedidos_recibidos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='pedidos')
    cantidad = models.IntegerField()
    forma_entrega = models.CharField(max_length=10, choices=ENTREGA_CHOICES)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Pedido {self.id} - {self.tecnico} a {self.proveedor}"


class Credito(models.Model):
    """Límite de crédito entre proveedor y técnico (US-10, US-11, US-12)"""
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='creditos')
    tecnico = models.ForeignKey(Tecnico, on_delete=models.CASCADE, related_name='creditos')
    limite = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_usado = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Crédito"
        verbose_name_plural = "Créditos"
        unique_together = ('proveedor', 'tecnico')

    def __str__(self):
        return f"Crédito {self.tecnico.usuario.username} con {self.proveedor.nombre_negocio}"


class CalificacionProveedor(models.Model):
    """Calificación de proveedor por técnico (US-13)"""
    tecnico = models.ForeignKey(Tecnico, on_delete=models.CASCADE, related_name='calificaciones_dadas')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='calificaciones_recibidas')
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='calificacion_proveedor')
    estrellas = models.IntegerField(choices=[(i, f"{i} estrella{'s' if i != 1 else ''}") for i in range(1, 6)])
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
    puntualidad = models.IntegerField(choices=[(i, f"{i} estrella{'s' if i != 1 else ''}") for i in range(1, 6)])
    trato = models.IntegerField(choices=[(i, f"{i} estrella{'s' if i != 1 else ''}") for i in range(1, 6)])
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