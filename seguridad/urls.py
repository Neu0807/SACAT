from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('inicio/', views.inicio_view, name='inicio'),
    path('salir/', views.salir_sistema, name='salir_sistema'),
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/nuevo-sistema/', views.crear_superusuario_view, name='crear_superusuario'),
    path('usuarios/guardar/', views.guardar_superusuario, name='guardar_superusuario'),
    path('usuarios/cambiar-estado/<str:username>/', views.cambiar_estado_usuario, name='cambiar_estado_usuario'),
    path('usuarios/reset-clave/<str:username>/', views.resetear_clave_usuario, name='resetear_clave_usuario'),
    path('usuarios/editar/<str:username>/', views.editar_usuario_view, name='editar_usuario'),
    path('seguridad/actualizar-clave/', views.cambiar_clave_obligatorio_view, name='cambiar_clave_obligatorio'),
    path('roles/', views.listar_roles, name='listar_roles'),
    path('roles/crear/', views.crear_rol_view, name='crear_rol'), 
    path('roles/guardar/', views.guardar_rol, name='guardar_rol'),
    path('roles/editar/<int:rol_id>/', views.editar_rol_view, name='editar_rol'),
    path('roles/cambiar-estado/<int:rol_id>/', views.cambiar_estado_rol, name='cambiar_estado_rol'),
    path('permisos/', views.listar_permisos, name='listar_permisos'),
    path('permisos/crear/', views.crear_permiso, name='crear_permiso'),
    path('permisos/guardar/', views.guardar_permiso, name='guardar_permiso'),
    path('permisos/cambiar-estado/<int:pk>/', views.cambiar_estado_permiso, name='cambiar_estado_permiso'),
]