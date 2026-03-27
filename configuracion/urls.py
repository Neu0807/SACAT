from django.urls import path
from . import views

urlpatterns = [
    path('ubicacion/', views.configuracion_ubicacion, name='configuracion_ubicacion'),
    path('ubicacion/estados/', views.listar_estados, name='listar_estados'),
    path('ubicacion/municipios/', views.listar_municipios, name='listar_municipios'),
    path('ubicacion/parroquias/', views.listar_parroquias, name='listar_parroquias'),
    path('ubicacion/importar-estados/', views.importar_estados, name='importar_estados'),
    path('ubicacion/importar-municipios/', views.importar_municipios, name='importar_municipios'),
    path('ubicacion/importar-parroquias/', views.importar_parroquias, name='importar_parroquias'),
    
    # Rutas de Identidad - CORREGIDAS
    path('identidad/', views.configuracion_identidad, name='configuracion_identidad'),
    path('identidad/documentos/', views.listar_tipos_docs, name='listar_tipos_docs'),
    path('identidad/sexos/', views.listar_sexos, name='listar_sexos'),
    path('identidad/estados-civiles/', views.listar_estados_civiles, name='listar_estados_civiles'),
    path('identidad/contactos/', views.listar_tipos_contactos, name='listar_tipos_contactos'),
    
    # ESTA ES LA QUE TE DABA EL ERROR NoReverseMatch
    path('identidad/documentos/crear/', views.crear_tipo_documento, name='crear_tipo_documento'),
    
    # Toggles
    path('estados/toggle/<int:estado_id>/', views.toggle_estado, name='toggle_estado'),
    path('municipios/toggle/<int:municipio_id>/', views.toggle_municipio, name='toggle_municipio'),
    path('parroquias/toggle/<int:parroquia_id>/', views.toggle_parroquia, name='toggle_parroquia'),
    
    # Menús restantes
    path('institucion/', views.configuracion_institucion, name='configuracion_institucion'),
    path('estructura/', views.configuracion_estructura, name='configuracion_estructura'),
    path('laboral/', views.configuracion_laboral, name='configuracion_laboral'),
    path('entorno/', views.configuracion_entorno, name='configuracion_entorno'),
    path('dotacion/', views.configuracion_dotacion, name='configuracion_dotacion'),
    path('electoral/', views.configuracion_electoral, name='configuracion_electoral'),
    path('identidad/documentos/toggle/<int:doc_id>/', views.toggle_tipo_doc, name='toggle_tipo_doc'),
    path('identidad/documentos/editar/<int:doc_id>/', views.editar_tipo_documento, name='editar_tipo_documento'),
]