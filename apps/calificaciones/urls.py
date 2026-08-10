from django.urls import path

from . import views


urlpatterns = [
    path('calificaciones/proveedor/<int:pedido_pk>/', views.calificar_proveedor, name='calificar_proveedor'),
    path('calificaciones/tecnico/<int:pedido_pk>/', views.calificar_tecnico, name='calificar_tecnico'),
]
