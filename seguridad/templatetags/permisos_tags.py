# seguridad/templatetags/permisos_tags.py
from django import template
from ..models import RolPermiso

register = template.Library()


@register.simple_tag(takes_context=True)
def tiene_permiso(context, permiso_nombre):
    """
    Verifica si el usuario actual tiene un permiso específico.
    
    Uso en templates:
        {% load permisos_tags %}
        {% tiene_permiso 'ver_usuarios' as puede_ver_usuarios %}
        {% if puede_ver_usuarios %} ... {% endif %}
    
    O directamente:
        {% if tiene_permiso 'ver_usuarios' %} ... {% endif %}
    """
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    
    # Superuser siempre tiene todos los permisos
    if request.user.is_superuser:
        return True
    
    # Verificar si tiene rol y si el rol está activo
    if not request.user.rol or not request.user.rol.esta_activo:
        return False
    
    # Buscar el permiso en la tabla intermedia
    return RolPermiso.objects.filter(
        rol=request.user.rol,
        permiso_sis__nombre_permiso=permiso_nombre,
        permiso_sis__esta_activo=True,
        esta_activo=True
    ).exists()


@register.simple_tag(takes_context=True)
def permisos_usuario(context):
    """
    Retorna una lista con los nombres de todos los permisos activos del usuario.
    Útil para debug o lógica avanzada en JS.
    """
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return []
    
    if request.user.is_superuser:
        from ..models import PermisoSis
        return list(PermisSis.objects.filter(esta_activo=True).values_list('nombre_permiso', flat=True))
    
    if not request.user.rol or not request.user.rol.esta_activo:
        return []
    
    return list(
        RolPermiso.objects.filter(
            rol=request.user.rol,
            permiso_sis__esta_activo=True,
            esta_activo=True
        ).values_list('permiso_sis__nombre_permiso', flat=True)
    )