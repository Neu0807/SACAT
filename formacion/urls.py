from django.urls import path
from . import views

urlpatterns = [
    # Ofertas
    path('ofertas/', views.listar_ofertas, name='listar_ofertas'),
    path('ofertas/crear/', views.crear_oferta, name='crear_oferta'),
    path('ofertas/editar/<int:oferta_id>/', views.editar_oferta, name='editar_oferta'),
    path('ofertas/toggle/<int:oferta_id>/', views.toggle_oferta, name='toggle_oferta'),

    # Postulaciones
    path('postulaciones/', views.listar_ofertas_activas, name='listar_ofertas_activas'),
    path('postulaciones/postular/<int:oferta_id>/', views.postular_oferta, name='postular_oferta'),
    path('postulaciones/historial/', views.listar_postulaciones, name='listar_postulaciones'),

    path('aprobacion/', views.bandeja_aprobacion, name='bandeja_aprobacion'),
    path('aprobacion/aprobar/<int:postulacion_id>/', views.aprobar_jefe, name='aprobar_jefe'),
    path('aprobacion/rechazar/<int:postulacion_id>/', views.rechazar_jefe, name='rechazar_jefe'),
    path('aprobacion/aprobar_gh/<int:postulacion_id>/', views.aprobar_gh, name='aprobar_gh'),
    path('aprobacion/rechazar_gh/<int:postulacion_id>/', views.rechazar_gh, name='rechazar_gh'),

    # Planificación
    path('planificacion/grupos/<int:oferta_id>/', views.listar_grupos, name='listar_grupos'),
    path('planificacion/grupos/<int:oferta_id>/crear/', views.crear_grupo, name='crear_grupo'),
    path('planificacion/grupos/editar/<int:grupo_id>/', views.editar_grupo, name='editar_grupo'),
    # Detalle para modales (AJAX)
path('aprobacion/detalle-jefe/<int:oferta_id>/', views.detalle_jefe, name='detalle_jefe'),
path('aprobacion/detalle-gh/<int:oferta_id>/', views.detalle_gh, name='detalle_gh'),
]