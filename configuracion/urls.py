from django.urls import path
from . import views

urlpatterns = [
    # =========================================================================
    # MÓDULO: UBICACIÓN (completo)
    # =========================================================================
    path('ubicacion/', views.configuracion_ubicacion, name='configuracion_ubicacion'),

    # --- Estados ---
    path('ubicacion/estados/', views.listar_estados, name='listar_estados'),
    path('ubicacion/estados/toggle/<int:estado_id>/', views.toggle_estado, name='toggle_estado'),
    path('ubicacion/estados/importar/', views.importar_estados, name='importar_estados'),

    # --- Municipios ---
    path('ubicacion/municipios/', views.listar_municipios, name='listar_municipios'),
    path('ubicacion/municipios/toggle/<int:municipio_id>/', views.toggle_municipio, name='toggle_municipio'),
    path('ubicacion/municipios/importar/', views.importar_municipios, name='importar_municipios'),

    # --- Parroquias ---
    path('ubicacion/parroquias/', views.listar_parroquias, name='listar_parroquias'),
    path('ubicacion/parroquias/toggle/<int:parroquia_id>/', views.toggle_parroquia, name='toggle_parroquia'),
    path('ubicacion/parroquias/importar/', views.importar_parroquias, name='importar_parroquias'),

    # =========================================================================
    # MÓDULO: IDENTIDAD (solo lo que ya tiene vista)
    # =========================================================================
    path('identidad/', views.configuracion_identidad, name='configuracion_identidad'),

    # --- Tipos de documento de identidad ---
    path('identidad/documentos/', views.listar_tipos_docs, name='listar_tipos_docs'),
    path('identidad/documentos/crear/', views.crear_tipo_documento, name='crear_tipo_documento'),
    path('identidad/documentos/editar/<int:doc_id>/', views.editar_tipo_documento, name='editar_tipo_documento'),
    path('identidad/documentos/toggle/<int:doc_id>/', views.toggle_tipo_doc, name='toggle_tipo_doc'),

    # --- Sexos (solo listar por ahora) ---
    path('identidad/sexos/', views.listar_sexos, name='listar_sexos'),
    # path('identidad/sexos/toggle/<int:sexo_id>/', views.toggle_sexo, name='toggle_sexo'),  # Pendiente vista toggle_sexo

    # --- Estados civiles (solo listar) ---
    path('identidad/estados-civiles/', views.listar_estados_civiles, name='listar_estados_civiles'),
    # path('identidad/estados-civiles/toggle/<int:estadocivil_id>/', views.toggle_estado_civil, name='toggle_estado_civil'),  # Pendiente

    # --- Tipos de contacto (solo listar) ---
    path('identidad/contactos/', views.listar_tipos_contactos, name='listar_tipos_contactos'),
    # path('identidad/contactos/toggle/<int:contacto_id>/', views.toggle_tipo_contacto, name='toggle_tipo_contacto'),  # Pendiente

    # =========================================================================
    # MÓDULO: ENTORNO (próximamente)
    # =========================================================================
    path('entorno/', views.configuracion_entorno, name='configuracion_entorno'),
    # path('entorno/tipos-vivienda/', views.listar_tipos_viviendas, name='listar_tipos_viviendas'),
    # etc...

    # =========================================================================
    # MÓDULO: LABORAL (próximamente)
    # =========================================================================
    path('laboral/', views.configuracion_laboral, name='configuracion_laboral'),

    # =========================================================================
    # MÓDULO: DOTACIÓN (Ítems y tallas)
    # =========================================================================
    path('dotacion/', views.configuracion_dotacion, name='configuracion_dotacion'),

    # --- Ítems de dotación ---
    path('dotacion/items/', views.listar_items_dotaciones, name='listar_items_dotaciones'),
    path('dotacion/items/toggle/<int:item_id>/', views.toggle_item_dotacion, name='toggle_item_dotacion'),

    # --- Tallas de dotación ---
    path('dotacion/tallas/', views.listar_tallas_dotaciones, name='listar_tallas_dotaciones'),
    path('dotacion/tallas/toggle/<int:talla_id>/', views.toggle_talla_dotacion, name='toggle_talla_dotacion'),

    # =========================================================================
    # MÓDULO: INSTITUCIÓN Y ESTRUCTURA (menús sin CRUD aún)
    # =========================================================================
    path('institucion/', views.configuracion_institucion, name='configuracion_institucion'),
    path('estructura/', views.configuracion_estructura, name='configuracion_estructura'),

    # =========================================================================
    # MÓDULO: ELECTORAL (completo)
    # =========================================================================
    path('electoral/', views.configuracion_electoral, name='configuracion_electoral'),
    path('electoral/centros/', views.listar_centros_votaciones, name='listar_centros_votaciones'),
    path('electoral/centros/importar/', views.importar_centros_votaciones, name='importar_centros_votaciones'),
    path('electoral/centros/toggle/<int:centro_id>/', views.toggle_centro_votacion, name='toggle_centro_votacion'),

    # =========================================================================
    # API INTERNA
    # =========================================================================
    path('api/centros/<int:parroquia_id>/', views.get_centros_por_parroquia, name='get_centros'),
]