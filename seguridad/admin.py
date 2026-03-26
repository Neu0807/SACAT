from django.contrib import admin
from .models import Usuario, Rol, PermisoSis

# 1. Registro del Usuario con personalización (Usamos el decorador)
@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombre_usuario', 'rol', 'is_superuser', 'esta_activo', 'last_login')
    search_fields = ('nombre_usuario',)
    list_filter = ('rol', 'is_superuser', 'esta_activo')

# 2. Registro de los otros modelos (Sin personalización extra por ahora)
admin.site.register(Rol)
admin.site.register(PermisoSis)

# 3. Personalización del título del panel
admin.site.site_header = "SACAT - Almacenadora Caracas"
admin.site.site_title = "Panel Administrativo"
admin.site.index_title = "Gestión del Sistema"