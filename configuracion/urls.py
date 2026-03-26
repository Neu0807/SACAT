from django.urls import path # <--- ESTA ES LA LÍNEA QUE FALTA
from . import views

urlpatterns = [
    path('ubicacion/', views.configuracion_ubicacion, name='configuracion_ubicacion'),
    path('ubicacion/estados/', views.listar_estados, name='listar_estados'),
    path('ubicacion/municipios/', views.listar_municipios, name='listar_municipios'),
    path('ubicacion/parroquias/', views.listar_parroquias, name='listar_parroquias'),
    path('ubicacion/importar-estados/', views.importar_estados, name='importar_estados'),
    path('ubicacion/importar-municipios/', views.importar_municipios, name='importar_municipios'),
    path('ubicacion/importar-parroquias/', views.importar_parroquias, name='importar_parroquias'),
    # Rutas de Identificación
    path('identificacion/', views.configuracion_identificacion, name='configuracion_identificacion'),
    path('identificacion/documentos/', views.listar_tipos_docs, name='listar_tipos_docs'),
    path('identificacion/sexos/', views.listar_sexos, name='listar_sexos'),
    path('identificacion/estados-civiles/', views.listar_estados_civiles, name='listar_estados_civiles'),
    path('identificacion/tipos-contactos/', views.listar_tipos_contactos, name='listar_tipos_contactos'),
    path('identificacion/documentos/crear/', views.crear_tipo_documento, name='crear_tipo_documento'),
]