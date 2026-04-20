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

# Pedidos (Basado en US-07, US-08, US-09)
class Order(models.Model):
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
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='ordenes')
    cantidad = models.IntegerField()
    forma_entrega = models.CharField(max_length=10, choices=ENTREGA_CHOICES)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    notas = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Pedido {self.id} - {self.tecnico} a {self.proveedor}"

# Gestión de Créditos (Basado en US-11 y DER)
class Credito(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)
    tecnico = models.ForeignKey(Tecnico, on_delete=models.CASCADE)
    limite = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_usado = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Crédito de {self.tecnico} con {self.proveedor}"