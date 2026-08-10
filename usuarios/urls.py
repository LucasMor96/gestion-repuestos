from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import moderacion, views


urlpatterns = [
    path('registro/', views.registro_tipo, name='registro_tipo'),
    path('registro/tecnico/', views.registro_tecnico, name='registro_tecnico'),
    path('registro/proveedor/', views.registro_proveedor, name='registro_proveedor'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='usuarios/password_reset_form.html',
            email_template_name='usuarios/password_reset_email.txt',
            html_email_template_name='usuarios/password_reset_email.html',
            subject_template_name='usuarios/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'password-reset/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='usuarios/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='usuarios/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/completo/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='usuarios/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
    path('espera-aprobacion/', views.espera_aprobacion, name='espera_aprobacion'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/tecnico/<int:pk>/', views.perfil_tecnico, name='perfil_tecnico'),
    path('perfil/proveedor/<int:pk>/', views.perfil_proveedor, name='perfil_proveedor'),
    path('moderacion/', moderacion.panel_moderacion, name='panel_moderacion'),
    path('moderacion/aprobar/<str:tipo>/<int:pk>/', moderacion.aprobar_usuario, name='aprobar_usuario'),
    path('moderacion/rechazar/<str:tipo>/<int:pk>/', moderacion.rechazar_usuario, name='rechazar_usuario'),
    path('moderacion/suspender/<str:tipo>/<int:pk>/', moderacion.suspender_usuario, name='suspender_usuario'),
    path('moderacion/solicitar-info/<str:tipo>/<int:pk>/', moderacion.solicitar_info, name='solicitar_info'),
]
