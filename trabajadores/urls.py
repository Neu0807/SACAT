from django.urls import path
from . import views

urlpatterns = [
    # Paso 1
    path('registro/paso-1/', views.registro_paso1, name='registro_paso1'),
    path('registro/paso-1/guardar/', views.guardar_paso1, name='guardar_paso1'),
    
    # Paso 2
    path('registro/paso-2/', views.registro_paso2, name='registro_paso2'),
    path('registro/paso-2/guardar/', views.guardar_paso2, name='guardar_paso2'),
    
    # Selects Dinámicos
    path('get-municipios/<int:estado_id>/', views.get_municipios, name='get_municipios'),
    path('get-parroquias/<int:municipio_id>/', views.get_parroquias, name='get_parroquias'),
]