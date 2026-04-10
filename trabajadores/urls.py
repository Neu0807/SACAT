from django.urls import path
from . import views

urlpatterns = [
    # ==========================================================================
    # VERSIÓN 2: REGISTRO POR FASES (FASE 1: GESTIÓN HUMANA)
    # ==========================================================================
    
    # F1 - Paso 1: Identidad
    path('registrov2/fase1/paso-1/', views.registro_paso1_v2, name='registro_paso1_v2'),
    path('guardar-paso1-v2/', views.guardar_paso1_v2, name='guardar_paso1_v2'),

    # F1 - Paso 2: Contactos
    path('registrov2/fase1/paso-2/', views.registro_paso2_v2, name='paso2_contactos_f1'),
    path('guardar-paso2-v2/', views.guardar_paso2_v2, name='guardar_paso2_v2'),

    # F1 - Paso 3: Asignación Laboral
    path('registrov2/fase1/paso-3/', views.registro_paso3_v2, name='paso3_laboral_f1'),
    path('registrov2/fase1/guardar-paso3/', views.guardar_paso3_v2, name='guardar_paso3_v2'),

    # F1 - Paso 4: Comprobante y Emisión de Credenciales
    path('registrov2/fase1/paso-4/', views.paso4_comprobante_v1, name='paso4_comprobante_f1'),
    path('finalizar-f1-v2/', views.finalizar_fase1_v2, name='finalizar_fase1_v2'),

    # Reporte e Impresión de Ficha Maestra v2
    path('registrov2/imprimir-ficha-inicial/<int:persona_id>/', views.generar_ficha_inicial_v2, name='imprimir_ficha_inicial'),

    # AJAX Específico (Sede + Nivel)
    path('ajax/get-unidades-v2/', views.get_unidades_v2, name='get_unidades_v2'),
    path('registrov2/verificar-cedula/', views.verificar_cedula_ajax, name='verificar_cedula_ajax'),

    # ==========================================================================
    # (RESPALDO) FLUJO DE REGISTRO ANTERIOR - 9 PASOS
    # ==========================================================================
    
    path('registro/paso-1/', views.registro_paso1, name='registro_paso1'),
    path('guardar-paso1/', views.guardar_paso1, name='guardar_paso1'),

    path('registro/paso-2/', views.registro_paso2, name='registro_paso2'),
    path('guardar-paso2/', views.guardar_paso2, name='guardar_paso2'),

    path('registro/paso-3/', views.registro_paso3, name='registro_paso3'),
    path('guardar-paso3/', views.guardar_paso3, name='guardar_paso3'),

    path('registro/paso-4/', views.registro_paso4, name='registro_paso4'),
    path('guardar-paso4/', views.guardar_paso4, name='guardar_paso4'),

    path('registro/paso-5/', views.registro_paso5, name='registro_paso5'),
    path('guardar-paso5/', views.guardar_paso5, name='guardar_paso5'),

    path('registro/paso-6/', views.registro_paso6, name='registro_paso6'),
    path('guardar-paso6/', views.guardar_paso6, name='guardar_paso6'),

    path('registro/paso-7/', views.registro_paso7, name='registro_paso7'),
    path('guardar-paso7/', views.guardar_paso7, name='guardar_paso7'),

    path('registro/paso-8/', views.registro_paso8, name='registro_paso8'),
    path('guardar-paso8/', views.guardar_paso8, name='guardar_paso8'),

    path('registro/paso-9/', views.registro_paso9, name='registro_paso9'),
    path('finalizar-registro/', views.finalizar_registro, name='finalizar_registro'),

    path('registro/imprimir-ficha/<int:persona_id>/', views.generar_pdf_ficha, name='imprimir_ficha_pdf'),

    # ==========================================================================
    # AUXILIARES AJAX (Compartidos)
    # ==========================================================================
    path('get-municipios/<int:estado_id>/', views.get_municipios, name='get_municipios'),
    path('get-parroquias/<int:municipio_id>/', views.get_parroquias, name='get_parroquias'),
    path('ajax/get-unidades-por-nivel/', views.get_unidades_por_nivel, name='get_unidades_por_nivel'),
]