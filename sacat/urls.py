from django.contrib import admin
from django.urls import path, include
from django.conf import settings # <--- Importante: para traer tus ajustes
from django.conf.urls.static import static # <--- Importante: para servir archivos

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('seguridad.urls')),
    path('configuracion/', include('configuracion.urls')),
    path('trabajadores/', include('trabajadores.urls')),
    path('formacion/', include('formacion.urls')),
]

# --- ¡AGREGA ESTO AQUÍ ABAJO! ---
# Esto le dice a Django: "Si estamos en modo desarrollo, muestra lo que hay en media"
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)