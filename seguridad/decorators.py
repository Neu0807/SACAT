# seguridad/decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from functools import wraps
from .models import RolPermiso

def permiso_requerido(permiso_nombre):
    """
    Decorador que verifica si el usuario (a través de su rol) tiene un permiso específico.
    
    Uso:
        @login_required
        @permiso_requerido('ver_usuarios')
        def listar_usuarios(request):
            ...
    
    Jerarquía de verificación:
    1. Superusuario -> ACCESO TOTAL (no se verifica nada más)
    2. Usuario sin rol -> DENEGADO
    3. Rol inactivo -> DENEGADO
    4. Busca el permiso en roles_permisos -> PERMITE o DENIEGA
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. SUPERUSUARIOS: Pase directo sin verificar nada
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # 2. Verificar si el usuario tiene un rol asignado
            if not request.user.rol:
                messages.error(request, "No tienes un rol asignado. Contacta al administrador.")
                return redirect('inicio')
            
            # 3. Verificar si el rol está activo
            if not request.user.rol.esta_activo:
                messages.error(request, "Tu rol está inactivo. Contacta al administrador.")
                return redirect('inicio')
            
            # 4. Buscar el permiso específico en la tabla intermedia
            tiene_permiso = RolPermiso.objects.filter(
                rol=request.user.rol,
                permiso_sis__nombre_permiso=permiso_nombre,
                permiso_sis__esta_activo=True,
                esta_activo=True
            ).exists()
            
            if tiene_permiso:
                return view_func(request, *args, **kwargs)
            
            # 5. Si llega aquí, no tiene el permiso
            messages.error(request, f"No tienes el permiso necesario para esta acción.")
            return redirect('inicio')
        
        return _wrapped_view
    return decorator