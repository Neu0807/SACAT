from django.contrib import admin
from django.urls import path, include
from django.conf import settings 
from django.conf.urls.static import static 
from django.shortcuts import redirect  # <--- 1. Importas el redirect aquí arriba

urlpatterns = [
    # 2. Agregas esta línea para redirigir la raíz directamente al login
    path('', lambda request: redirect('login', permanent=False)),
    
    path('admin/', admin.site.urls),
    path('', include('seguridad.urls')),
    path('configuracion/', include('configuracion.urls')),
    path('trabajadores/', include('trabajadores.urls')),
    path('formacion/', include('formacion.urls')),
]

# --- Para servir archivos multimedia en desarrollo ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)