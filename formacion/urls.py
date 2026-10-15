from django.urls import path
from . import views

app_name = 'formacion'

urlpatterns = [
    # ==========================================================================
    # 🛠️ WORKSPACE DE GESTIÓN HUMANA
    # ==========================================================================
    # Tablero principal (KPIs globales + grid de ofertas)
    path('gestion/', views.listar_ofertas, name='listar_ofertas'),

    # CRUD de Ofertas
    path('gestion/oferta/crear/', views.crear_oferta, name='crear_oferta'),
    path('gestion/oferta/<int:oferta_id>/editar/', views.editar_oferta, name='editar_oferta'),
    path('gestion/oferta/<int:oferta_id>/toggle/', views.toggle_oferta, name='toggle_oferta'),
    path('gestion/oferta/<int:oferta_id>/cambiar-estado/', views.cambiar_estado_oferta, name='cambiar_estado_oferta'),

    # Workspace del Curso (contenedor de las 4 pestañas)
    path('gestion/oferta/<int:oferta_id>/workspace/', views.workspace_curso_view, name='workspace_curso'),

    # Pestaña 1: Postulaciones y Aprobación
    path('gestion/oferta/<int:oferta_id>/postulaciones/', views.workspace_postulaciones, name='workspace_postulaciones'),
    path('gestion/postulacion/<int:postulacion_id>/aprobar/', views.aprobar_gh, name='aprobar_gh'),
    path('gestion/oferta/<int:oferta_id>/aprobar-masivo/', views.aprobar_masivo_gh, name='aprobar_masivo_gh'),
    path('gestion/postulacion/<int:postulacion_id>/rechazar/', views.rechazar_gh, name='rechazar_gh'),
    path('gestion/oferta/<int:oferta_id>/inscribir-directo/', views.inscribir_trabajador_gh, name='inscribir_trabajador_gh'),
    path('gestion/postulacion/<int:postulacion_id>/sustituir/', views.sustituir_participante_gh, name='sustituir_participante_gh'),

    # Pestaña 2: Grupos y PDF
    path('gestion/oferta/<int:oferta_id>/grupos/', views.listar_grupos, name='listar_grupos'),
    path('gestion/oferta/<int:oferta_id>/grupo/crear/', views.crear_grupo, name='crear_grupo'),
    path('gestion/grupo/<int:grupo_id>/editar/', views.editar_grupo, name='editar_grupo'),
    path('gestion/grupo/<int:grupo_id>/pdf/', views.descargar_lista_asistencia_pdf, name='lista_asistencia_pdf'),

    # Pestaña 3: Asistencia
    path('gestion/oferta/<int:oferta_id>/asistencia/', views.workspace_asistencia, name='workspace_asistencia'),
    path('gestion/grupo/<int:grupo_id>/guardar-asistencia/', views.guardar_asistencia_grupo, name='guardar_asistencia_grupo'),
    path('gestion/grupo/<int:grupo_id>/asistente-sitio/', views.agregar_asistente_sitio, name='agregar_asistente_sitio'),

    # Pestaña 4: Certificados
    path('gestion/postulacion/<int:postulacion_id>/cargar-certificado/', views.cargar_certificado, name='cargar_certificado_gh'),

    # ==========================================================================
    # 🎓 PORTAL DEL TRABAJADOR
    # ==========================================================================
    path('portal/', views.listar_ofertas_activas, name='listar_ofertas_activas'),
    path('portal/oferta/<int:oferta_id>/detalle/', views.detalle_oferta_trabajador, name='detalle_oferta_trabajador'),
    path('portal/oferta/<int:oferta_id>/postular/', views.postular_oferta, name='postular_oferta'),
    path('portal/postulacion/<int:postulacion_id>/cancelar/', views.cancelar_postulacion, name='cancelar_postulacion'),
    path('portal/postulacion/<int:postulacion_id>/cargar-certificado/', views.cargar_certificado, name='cargar_certificado_trabajador'),

    # Redirecciones legacy
    path('postulaciones/', views.listar_postulaciones, name='listar_postulaciones'),
    path('aprobacion/', views.bandeja_aprobacion, name='bandeja_aprobacion'),
]