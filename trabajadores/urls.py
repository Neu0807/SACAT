from django.urls import path
from . import views

urlpatterns = [
    # ==========================================================================
    # FLUJO DE REGISTRO - 9 PASOS
    # ==========================================================================
    
    # PASO 1: Datos Personales
    path('registro/paso-1/', views.registro_paso1, name='registro_paso1'),
    path('guardar-paso1/', views.guardar_paso1, name='guardar_paso1'),

    # PASO 2: Domicilio, Vivienda y Electoral
    path('registro/paso-2/', views.registro_paso2, name='registro_paso2'),
    path('guardar-paso2/', views.guardar_paso2, name='guardar_paso2'),

    # PASO 3: Contactos Personales y de Emergencia
    path('registro/paso-3/', views.registro_paso3, name='registro_paso3'),
    path('guardar-paso3/', views.guardar_paso3, name='guardar_paso3'),

    # PASO 4: Formación Académica
    path('registro/paso-4/', views.registro_paso4, name='registro_paso4'),
    path('guardar-paso4/', views.guardar_paso4, name='guardar_paso4'),

    # PASO 5: Formación Adicional (Adiestramiento)
    path('registro/paso-5/', views.registro_paso5, name='registro_paso5'),
    path('guardar-paso5/', views.guardar_paso5, name='guardar_paso5'),

    # PASO 6: Salud, Discapacidad y Patologías
    path('registro/paso-6/', views.registro_paso6, name='registro_paso6'),
    path('guardar-paso6/', views.guardar_paso6, name='guardar_paso6'),

    # PASO 7: Carga Familiar (Dinámico)
    path('registro/paso-7/', views.registro_paso7, name='registro_paso7'),
    path('guardar-paso7/', views.guardar_paso7, name='guardar_paso7'),

    # PASO 8: Relación Laboral (Asignación Institucional)
    path('registro/paso-8/', views.registro_paso8, name='registro_paso8'),
    path('guardar-paso8/', views.guardar_paso8, name='guardar_paso8'),

    # PASO 9: Credenciales, Envío de Correo y Cierre
    path('registro/paso-9/', views.registro_paso9, name='registro_paso9'),
    path('finalizar-registro/', views.finalizar_registro, name='finalizar_registro'),

    # trabajadores/urls.py
path('registro/imprimir-ficha/<int:persona_id>/', views.generar_pdf_ficha, name='imprimir_ficha_pdf'),

    # ==========================================================================
    # AUXILIARES AJAX (Geografía y Otros)
    # ==========================================================================
    path('get-municipios/<int:estado_id>/', views.get_municipios, name='get_municipios'),
    path('get-parroquias/<int:municipio_id>/', views.get_parroquias, name='get_parroquias'),
]