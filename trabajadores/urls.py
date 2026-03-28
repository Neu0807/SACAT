from django.urls import path
from . import views

urlpatterns = [
    # --- PASO 1: Identidad ---
    path('registro/paso-1/', views.registro_paso1, name='registro_paso1'),
    path('guardar-paso1/', views.guardar_paso1, name='guardar_paso1'),

    # --- PASO 2: Ubicación Geográfica ---
    path('registro/paso-2/', views.registro_paso2, name='registro_paso2'),
    path('guardar-paso2/', views.guardar_paso2, name='guardar_paso2'),

    # --- PASO 3: Vivienda (EL QUE ESTAMOS ARMANDO) ---
    path('registro/paso-3/', views.registro_paso3, name='registro_paso3'),
    path('guardar-paso3/', views.guardar_paso3, name='guardar_paso3'),

    # --- PASO 4: Contactos Personales (PRÓXIMO) ---
    path('registro/paso-4/', views.registro_paso4, name='registro_paso4'),
    path('guardar-paso4/', views.guardar_paso4, name='guardar_paso4'),

    # --- AUXILIARES AJAX (Para los select dinámicos) ---
    path('get-municipios/<int:estado_id>/', views.get_municipios, name='get_municipios'),
    path('get-parroquias/<int:municipio_id>/', views.get_parroquias, name='get_parroquias'),
]