from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

# --- 1. MODELO DE PERMISOS (Tabla: permisos_sis) ---
# Se pone de primero porque Rol y RolPermiso dependen de él
class PermisoSis(models.Model):
    nombre_permiso = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'permisos_sis'
        managed = False # Django no tocará esta tabla, ya existe en tu DB
        verbose_name = "Permiso del Sistema"

    def __str__(self):
        return self.nombre_permiso

# --- 2. MODELO DE ROLES (Tabla: roles) ---
class Rol(models.Model):
    nombre_rol = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Relación ManyToMany usando tu tabla intermedia
    permisos = models.ManyToManyField(
        PermisoSis, 
        through='RolPermiso', 
        related_name='roles'
    )

    class Meta:
        db_table = 'roles'
        managed = False

    def __str__(self):
        return self.nombre_rol

# --- 3. MODELO INTERMEDIO (Tabla: roles_permisos) ---
class RolPermiso(models.Model):
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, db_column='rol_id')
    permiso_sis = models.ForeignKey(PermisoSis, on_delete=models.CASCADE, db_column='permiso_sis_id')
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roles_permisos'
        managed = False

# --- 4. MANAGER DE USUARIO ---
class UsuarioManager(BaseUserManager):
    def create_user(self, nombre_usuario, password=None, **extra_fields):
        if not nombre_usuario:
            raise ValueError('El usuario debe tener una cédula (nombre_usuario)')
        user = self.model(nombre_usuario=nombre_usuario, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, nombre_usuario, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(nombre_usuario, password, **extra_fields)

# --- 5. MODELO DE USUARIO (Tabla: usuarios) ---
class Usuario(AbstractBaseUser):
    # Mapeo de campos de Django a tus columnas en español
    password = models.CharField(max_length=128, db_column='contrasena_hash')
    last_login = models.DateTimeField(null=True, blank=True, db_column='ultimo_acceso')
    is_staff = models.BooleanField(default=False, db_column='es_staff')
    is_superuser = models.BooleanField(default=False, db_column='es_superusuario')

    # Tus campos reales
    nombre_usuario = models.CharField(max_length=50, unique=True)
    requiere_cambio_clave = models.BooleanField(default=True)
    esta_activo = models.BooleanField(default=True)
    
    # Llaves foráneas reales
    trabajador_id = models.IntegerField(null=True, blank=True) 
    rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, blank=True, db_column='rol_id')

    # Auditoría
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    objects = UsuarioManager()
    USERNAME_FIELD = 'nombre_usuario'

    class Meta:
        db_table = 'usuarios'
        managed = False 

    def __str__(self):
        return self.nombre_usuario

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser