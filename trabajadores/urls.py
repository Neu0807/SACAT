from django.urls import path
from . import views

urlpatterns = [
    # ==========================================================================
    # 1. REGISTRO POR FASES (FASE 1: GESTIÓN HUMANA - V2)
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

    # F1 - Paso 4: Comprobante y Finalización
    path('registrov2/fase1/paso-4/', views.paso4_comprobante_v1, name='paso4_comprobante_f1'),
    path('finalizar-f1-v2/', views.finalizar_fase1_v2, name='finalizar_fase1_v2'),

    # Reporte e Impresión de Ficha Maestra v2
    path('registrov2/imprimir-ficha-inicial/<int:persona_id>/', views.generar_ficha_inicial_v2, name='imprimir_ficha_inicial'),

    # ==========================================================================
    # 2. GESTIÓN Y ADMINISTRACIÓN DE PERSONAL (MASTER LIST)
    # ==========================================================================
    
    # Listado Maestro de Trabajadores
    path('gestion/listado/', views.listar_trabajadores, name='listar_trabajadores'),
    path('gestion/perfil/<int:trabajador_id>/', views.perfil_trabajador, name='perfil_trabajador'),
    
    # Detalle en Modal vía AJAX
    path('ajax/detalle-trabajador/<int:trabajador_id>/', views.detalle_trabajador_json, name='detalle_trabajador_json'),

    # ==========================================================================
    # 3. CONSULTAS EXTERNAS Y VALIDACIONES (PNP / SENIAT / AJAX)
    # ==========================================================================
    
    # Consulta Oficial SENIAT (Integradas)
    path('obtener-captcha-seniat/', views.obtener_captcha_seniat, name='obtener_captcha_seniat'),
    path('consultar-datos-seniat/', views.consultar_datos_seniat, name='consultar_datos_seniat'),

    # Verificaciones AJAX
    path('registrov2/verificar-cedula/', views.verificar_cedula_ajax, name='verificar_cedula_ajax'),
    path('ajax/get-unidades-v2/', views.get_unidades_v2, name='get_unidades_v2'),
    
    # Auxiliares Geográficos y Jerárquicos
    path('get-municipios/<int:estado_id>/', views.get_municipios, name='get_municipios'),
    path('get-parroquias/<int:municipio_id>/', views.get_parroquias, name='get_parroquias'),
    path('ajax/get-unidades-por-nivel/', views.get_unidades_por_nivel, name='get_unidades_por_nivel'),


    # ==========================================================================
    # FASE 2: COMPLETACIÓN DE DATOS (AUTOGESTIÓN TRABAJADOR)
    # ==========================================================================
    path('autogestion/paso-1/', views.f2_paso1_identidad, name='f2_paso1_identidad'),
    path('autogestion/paso-1/guardar/', views.guardar_f2_paso1, name='guardar_f2_paso1'),   # ← NUEVA
    path('autogestion/paso-2/', views.f2_paso2_contactos, name='f2_paso2_contactos'),
    path('autogestion/paso-2/guardar/', views.guardar_f2_paso2, name='guardar_f2_paso2'),
    path('autogestion/paso-3/', views.f2_paso3_formacion, name='f2_paso3_formacion'),
    path('autogestion/paso-3/guardar/', views.guardar_f2_paso3, name='guardar_f2_paso3'),
    path('autogestion/paso-4/', views.f2_paso4_adiestramiento, name='f2_paso4_adiestramiento'),
    path('autogestion/paso-4/guardar/', views.guardar_f2_paso4, name='guardar_f2_paso4'),
    path('autogestion/paso-5/', views.f2_paso5_salud, name='f2_paso5_salud'),
    path('autogestion/paso-5/guardar/', views.guardar_f2_paso5, name='guardar_f2_paso5'),
    path('autogestion/paso-6/', views.f2_paso6_familia, name='f2_paso6_familia'),
    path('autogestion/paso-6/guardar/', views.guardar_f2_paso6, name='guardar_f2_paso6'),
    path('autogestion/paso-7/', views.f2_paso7_laboral, name='f2_paso7_laboral'),
    path('autogestion/comprobante/', views.f2_comprobante, name='f2_comprobante'),
    path('autogestion/generar-pdf/<int:trabajador_id>/', views.generar_ficha_completa_v2, name='generar_ficha_completa_v2'),
    

    # ==========================================================================
    # 4. (RESPALDO) FLUJO DE REGISTRO ANTERIOR - 9 PASOS
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
]