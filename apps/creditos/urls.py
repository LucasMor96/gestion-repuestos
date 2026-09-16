from django.urls import path

from . import views


urlpatterns = [
    path('credito/', views.mis_creditos, name='mis_creditos'),
    path('credito/pagar/<int:pk>/', views.pagar_credito, name='pagar_credito'),
    path('credito/gestionar/', views.gestionar_creditos_proveedor, name='gestionar_creditos_proveedor'),
    path('credito/asignar/', views.asignar_credito, name='asignar_credito'),
    path('credito/revocar/<int:pk>/', views.revocar_credito, name='revocar_credito'),
    path('credito/deudas/', views.deudas_tecnicos, name='deudas_tecnicos'),
    path('credito/deudas/<int:pk>/', views.detalle_deuda_tecnico, name='detalle_deuda_tecnico'),
    path('credito/saldar/<int:pk>/', views.marcar_deuda_saldada, name='marcar_deuda_saldada'),
    path('credito/pagos/<int:pk>/confirmar/', views.confirmar_pago_credito, name='confirmar_pago_credito'),
    path('credito/pagos/<int:pk>/rechazar/', views.rechazar_pago_credito, name='rechazar_pago_credito'),
]
