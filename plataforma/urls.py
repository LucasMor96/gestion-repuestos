from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro_tipo, name='registro_tipo'),
    path('registro/tecnico/', views.registro_tecnico, name='registro_tecnico'),
    path('registro/proveedor/', views.registro_proveedor, name='registro_proveedor'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('espera-aprobacion/', views.espera_aprobacion, name='espera_aprobacion'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
