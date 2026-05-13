import json
import secrets
import string
from django.views.decorators.http import require_POST
from django.contrib.auth import logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db import transaction  # 🆕 Necesario para gestionar_permisos_rol

# 🆕 Importamos el decorador personalizado de permisos
from .decorators import permiso_requerido

# IMPORTANTE: Importamos los modelos necesarios
from .models import Rol
from .models import PermisoSis
from .models import RolPermiso  # 🆕 Necesario para gestionar_permisos_rol

Usuario = get_user_model()


# =============================================================================
# FUNCIÓN AUXILIAR DE SEGURIDAD (INTERNA)
# =============================================================================

def generar_clave_robusta(longitud=12):
    letras_minus = string.ascii_lowercase + "ñ"
    letras_mayus = string.ascii_uppercase + "Ñ"
    numeros = string.digits
    especiales = "!@#$%&*+-=." 
    
    todos = letras_minus + letras_mayus + numeros + especiales
    
    while True:
        password = ''.join(secrets.choice(todos) for _ in range(longitud))
        if (any(c in letras_minus for c in password)
            and any(c in letras_mayus for c in password)
            and any(c in numeros for c in password)
            and any(c in especiales for c in password)
            and (len(password) >= 8)):
            return password


# =============================================================================
# VISTAS DE SESIÓN (PÚBLICAS)
# =============================================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('inicio') 

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cedula = data.get('cedula')
            password = data.get('password')
            user = authenticate(request, nombre_usuario=cedula, password=password)

            if user is not None:
                if user.esta_activo:
                    login(request, user)
                    return JsonResponse({
                        'success': True, 
                        'mensaje': '¡Bienvenido al sistema SACAT!',
                        'is_superuser': user.is_superuser
                    })
                else:
                    return JsonResponse({'success': False, 'mensaje': 'Cuenta suspendida.'})
            else:
                return JsonResponse({'success': False, 'mensaje': 'Cédula o contraseña incorrectas.'})
        except Exception:
            return JsonResponse({'success': False, 'mensaje': 'Error en el servidor.'})

    return render(request, 'login/login.html')


@login_required
def inicio_view(request):
    return render(request, 'login/inicio.html')


def salir_sistema(request):
    logout(request)
    return redirect('login')


# =============================================================================
# GESTIÓN DE USUARIOS
# =============================================================================

@login_required
@permiso_requerido('ver_usuarios')  # 🆕
def listar_usuarios(request):
    """Listar todos los usuarios del sistema."""
    usuarios = Usuario.objects.all().order_by('-id')
    return render(request, 'usuarios/listar_usuarios.html', {'usuarios': usuarios})


@login_required
@permiso_requerido('crear_usuario')  # 🆕
def crear_superusuario_view(request):
    """Formulario para crear un nuevo usuario."""
    return render(request, 'usuarios/crear_superusuario.html')


@login_required
@permiso_requerido('crear_usuario')  # 🆕
def guardar_superusuario(request):
    """Procesa la creación de un nuevo usuario (AJAX)."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cedula = data.get('nombre_usuario')
            
            if Usuario.objects.filter(nombre_usuario=cedula).exists():
                return JsonResponse({'success': False, 'mensaje': 'Esta cédula ya está registrada.'})

            clave_temporal = generar_clave_robusta(12)

            # 1. Buscamos el objeto Rol 'Superusuario' en tu tabla 'roles'
            try:
                rol_su = Rol.objects.get(nombre_rol='Superusuario')
            except Rol.DoesNotExist:
                return JsonResponse({'success': False, 'mensaje': 'Error Crítico: El rol Superusuario no existe en la tabla roles. Créalo en el /admin primero.'})

            # 2. Creamos el usuario base
            nuevo_user = Usuario.objects.create_user(
                nombre_usuario=cedula,
                password=clave_temporal
            )
            
            # 3. AUTOMATIZACIÓN: Si el rol es Superusuario, prendemos los interruptores de Django
            nuevo_user.rol = rol_su  # Se guarda en tu columna 'rol_id'
            
            # Aquí ocurre la magia:
            if rol_su.nombre_rol == 'Superusuario':
                nuevo_user.is_superuser = True  # Se guarda en 'es_superusuario'
                nuevo_user.is_staff = True      # Se guarda en 'es_staff'
            
            nuevo_user.requiere_cambio_clave = True
            nuevo_user.creado_por = request.user.id
            nuevo_user.save()

            return JsonResponse({
                'success': True, 
                'clave': clave_temporal,
                'mensaje': f'Usuario {cedula} creado y configurado como Superusuario automáticamente.'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'mensaje': f'Error: {str(e)}'})


@login_required
@permiso_requerido('inhabilitar_usuario')  # 🆕
def cambiar_estado_usuario(request, username):
    """Activar o inhabilitar un usuario."""
    if request.method == 'POST':
        user = get_object_or_404(Usuario, nombre_usuario=username)
        if request.user == user:
            return JsonResponse({'success': False, 'mensaje': 'No puedes inhabilitarte a ti mismo.'})
        
        user.esta_activo = not user.esta_activo 
        user.save()
        estado = "habilitado" if user.esta_activo else "inhabilitado"
        return JsonResponse({'success': True, 'mensaje': f'Usuario {estado} correctamente.'})


@login_required
@permiso_requerido('resetear_clave_usuario')  # 🆕
def resetear_clave_usuario(request, username):
    """Resetear la contraseña de un usuario."""
    if request.method == 'POST':
        user = get_object_or_404(Usuario, nombre_usuario=username)
        nueva_clave = generar_clave_robusta(12)
        
        user.set_password(nueva_clave)
        user.requiere_cambio_clave = True
        user.save()
        
        return JsonResponse({
            'success': True, 
            'clave': nueva_clave,
            'mensaje': f'La clave de {username} ha sido reseteada.'
        })


@login_required
@permiso_requerido('editar_usuario')  # 🆕
def editar_usuario_view(request, username):
    """Editar perfil de un usuario."""
    user_editar = get_object_or_404(Usuario, nombre_usuario=username)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_editar.is_superuser = True
            user_editar.is_staff = data.get('is_staff', True)
            user_editar.save()
            return JsonResponse({'success': True, 'mensaje': 'Permisos actualizados correctamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'mensaje': f'Error: {str(e)}'})
    return render(request, 'usuarios/editar_usuario.html', {'user_editar': user_editar})


# =============================================================================
# CAMBIO DE CLAVE OBLIGATORIO
# =============================================================================

@login_required
def cambiar_clave_obligatorio_view(request):
    """Vista para cambio de clave obligatorio en primer ingreso."""
    if not request.user.requiere_cambio_clave:
        return redirect('inicio')

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nueva_clave = data.get('nueva_clave')
            caracteres_especiales = "!@#$%&*+-=." 

            if (len(nueva_clave) < 8 or 
                not any(c.isdigit() for c in nueva_clave) or 
                not any(c.isupper() or c == 'Ñ' for c in nueva_clave) or
                not any(c.islower() or c == 'ñ' for c in nueva_clave) or
                not any(c in caracteres_especiales for c in nueva_clave)):
                
                return JsonResponse({
                    'success': False, 
                    'mensaje': 'La clave no cumple con los requisitos de seguridad.'
                })

            request.user.set_password(nueva_clave)
            request.user.requiere_cambio_clave = False
            request.user.save()
            logout(request)
            
            update_session_auth_hash(request, request.user)

            return JsonResponse({'success': True, 'mensaje': '¡Contraseña actualizada!'})
        except Exception as e:
            return JsonResponse({'success': False, 'mensaje': f'Error: {str(e)}'})

    return render(request, 'usuarios/cambiar_clave.html')


# =============================================================================
# SUBMÓDULO DE ROLES
# =============================================================================

@login_required
@permiso_requerido('crear_rol')  # 🆕
def crear_rol_view(request):
    """Carga el modal para crear un nuevo rol."""
    return render(request, 'roles/crear_rol.html')


@login_required
@permiso_requerido('ver_roles')  # 🆕
def listar_roles(request):
    """Listar todos los roles del sistema."""
    roles = Rol.objects.all().order_by('id')
    return render(request, 'roles/listar_roles.html', {'roles': roles})


@login_required
@permiso_requerido('crear_rol')  # 🆕
def guardar_rol(request):
    """Guardar un nuevo rol (AJAX)."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nombre = data.get('nombre_rol')
            descripcion = data.get('descripcion')

            if Rol.objects.filter(nombre_rol=nombre).exists():
                return JsonResponse({'success': False, 'mensaje': 'Este nombre de rol ya existe.'})

            nuevo_rol = Rol.objects.create(
                nombre_rol=nombre,
                descripcion=descripcion,
                creado_por=request.user.id # Auditoría automática
            )
            
            return JsonResponse({'success': True, 'mensaje': f'Rol "{nombre}" creado exitosamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'mensaje': str(e)})


@login_required
@permiso_requerido('editar_rol')  # 🆕
def editar_rol_view(request, rol_id):
    """Editar un rol existente."""
    rol = get_object_or_404(Rol, id=rol_id)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rol.nombre_rol = data.get('nombre_rol')
            rol.descripcion = data.get('descripcion')
            rol.actualizado_por = request.user.id
            rol.save()
            return JsonResponse({'success': True, 'mensaje': 'Rol actualizado correctamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'mensaje': str(e)})
            
    return render(request, 'roles/editar_rol.html', {'rol': rol})


@login_required
@permiso_requerido('inhabilitar_rol')  # 🆕
@require_POST
def cambiar_estado_rol(request, rol_id):
    """Activar o inhabilitar un rol."""
    rol = get_object_or_404(Rol, id=rol_id)
    
    if rol.nombre_rol == 'Superusuario':
        return JsonResponse({'success': False, 'mensaje': 'El rol Superusuario no puede ser modificado.'})
    
    # Alternar el estado
    rol.esta_activo = not rol.esta_activo
    rol.actualizado_por = request.user.id
    rol.save()
    
    estado = "habilitado" if rol.esta_activo else "inhabilitado"
    return JsonResponse({'success': True, 'mensaje': f'Rol {estado} correctamente.'})


# =============================================================================
# SUBMÓDULO DE PERMISOS
# =============================================================================

@login_required
@permiso_requerido('ver_permisos')  # 🆕
def listar_permisos(request):
    """Listar todos los permisos del sistema."""
    permisos = PermisoSis.objects.all().order_by('-fecha_creacion')
    return render(request, 'permisos/listar_permisos.html', {'permisos': permisos})


@login_required
@permiso_requerido('crear_permiso')  # 🆕
def crear_permiso(request):
    """Formulario para crear un nuevo permiso."""
    return render(request, 'permisos/crear_permiso.html')


@login_required
@permiso_requerido('crear_permiso')  # 🆕
def guardar_permiso(request):
    """Guardar un nuevo permiso (AJAX)."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nombre = data.get('nombre_permiso').strip().lower().replace(" ", "_") # Limpiamos el nombre
            descripcion = data.get('descripcion')

            # Validación: Evitar duplicados
            if PermisoSis.objects.filter(nombre_permiso=nombre).exists():
                return JsonResponse({'success': False, 'mensaje': f'El permiso "{nombre}" ya existe.'})

            # Creamos el registro
            PermisoSis.objects.create(
                nombre_permiso=nombre,
                descripcion=descripcion,
                creado_por=request.user.id if request.user.is_authenticated else None
            )
            return JsonResponse({'success': True, 'mensaje': 'Permiso creado exitosamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'mensaje': str(e)})
    return JsonResponse({'success': False, 'mensaje': 'Método no permitido'})


@login_required
@permiso_requerido('editar_permiso')  # 🆕
def editar_permiso(request, pk):
    """Editar un permiso existente."""
    permiso = get_object_or_404(PermisoSis, pk=pk)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            permiso.descripcion = data.get('descripcion')
            permiso.esta_activo = data.get('esta_activo')
            permiso.actualizado_por = request.user.id if request.user.is_authenticated else None
            permiso.save()
            return JsonResponse({'success': True, 'mensaje': 'Permiso actualizado.'})
        except Exception as e:
            return JsonResponse({'success': False, 'mensaje': str(e)})
            
    return render(request, 'permisos/editar_permiso.html', {'permiso': permiso})


@login_required
@permiso_requerido('inhabilitar_permiso')  # 🆕
@require_POST
def cambiar_estado_permiso(request, pk):
    """Activar o inhabilitar un permiso."""
    permiso = get_object_or_404(PermisoSis, pk=pk)
    permiso.esta_activo = not permiso.esta_activo
    permiso.actualizado_por = request.user.id if request.user.is_authenticated else None
    permiso.save()
    estado = "habilitado" if permiso.esta_activo else "inhabilitado"
    return JsonResponse({'success': True, 'mensaje': f'Permiso {estado} correctamente.'})


# =============================================================================
# ASIGNACIÓN DE PERMISOS A ROLES
# =============================================================================

@login_required
@permiso_requerido('asignar_permisos_rol')  # 🆕
def gestionar_permisos_rol(request, rol_id):
    """Gestionar los permisos asignados a un rol específico."""
    rol = get_object_or_404(Rol, id=rol_id)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            permisos_ids = data.get('permisos_ids', [])  # lista de IDs de permisos activos

            with transaction.atomic():
                # Desactivar todos los permisos actuales del rol
                RolPermiso.objects.filter(rol=rol).update(esta_activo=False)

                # Activar o crear los permisos que vienen en la lista
                for permiso_id in permisos_ids:
                    RolPermiso.objects.update_or_create(
                        rol=rol,
                        permiso_sis_id=permiso_id,
                        defaults={
                            'esta_activo': True,
                            'actualizado_por': request.user.id
                        }
                    )

            return JsonResponse({'success': True, 'mensaje': 'Permisos actualizados correctamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    # GET: mostrar la pantalla con todos los permisos y los que ya tiene el rol
    todos_permisos = PermisoSis.objects.filter(esta_activo=True).order_by('nombre_permiso')
    permisos_rol = RolPermiso.objects.filter(rol=rol, esta_activo=True).values_list('permiso_sis_id', flat=True)

    return render(request, 'permisos/gestionar_permisos_rol.html', {
        'rol': rol,
        'todos_permisos': todos_permisos,
        'permisos_rol': list(permisos_rol),
    })