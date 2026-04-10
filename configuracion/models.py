from django.db import models

# ==============================================================================
# CATEGORÍA 1: UBICACIÓN GEOGRÁFICA Y ELECTORAL
# ==============================================================================

class Estado(models.Model):
    nombre_estado = models.CharField(max_length=50)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'estados'
        managed = False 
    def __str__(self):
        return self.nombre_estado.upper()

class Municipio(models.Model):
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE, db_column='estado_id', related_name='municipios')
    nombre_municipio = models.CharField(max_length=100)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'municipios'
        managed = False
    def __str__(self):
        return f"{self.nombre_municipio.upper()} ({self.estado.nombre_estado})"

class Parroquia(models.Model):
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE, db_column='municipio_id', related_name='parroquias')
    nombre_parroquia = models.CharField(max_length=100)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'parroquias'
        managed = False
    def __str__(self):
        return self.nombre_parroquia.upper()

class CentroVotacion(models.Model):
    parroquia = models.ForeignKey(Parroquia, on_delete=models.PROTECT, db_column='parroquia_id')
    nombre_centro = models.CharField(max_length=150)
    codigo_cne = models.CharField(max_length=50, null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'centros_votaciones'
        managed = False
    def __str__(self):
        return self.nombre_centro.upper()

class Direccion(models.Model):
    parroquia = models.ForeignKey(Parroquia, on_delete=models.PROTECT, db_column='parroquia_id')
    direccion_exacta = models.TextField()
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'direcciones'
        managed = False

# ==============================================================================
# CATEGORÍA 2: IDENTIDAD, ENTORNO SOCIAL Y FAMILIA
# ==============================================================================

class TipoDocIdentificacion(models.Model):
    sigla = models.CharField(max_length=10)
    descripcion = models.CharField(max_length=50)
    ente_emisor = models.CharField(max_length=100, null=True, blank=True)
    aplica_a = models.CharField(max_length=50, null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tipos_docs_identificacion'
        managed = False
    def __str__(self):
        return f"{self.sigla} - {self.descripcion}"

class Sexo(models.Model):
    sigla = models.CharField(max_length=5)
    descripcion = models.CharField(max_length=30)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sexos'
        managed = False
    def __str__(self):
        return self.descripcion.upper()

class EstadoCivil(models.Model):
    sigla = models.CharField(max_length=5)
    descripcion = models.CharField(max_length=30)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'estados_civiles'
        managed = False
    def __str__(self):
        return self.descripcion.upper()

class Parentesco(models.Model):
    descripcion = models.CharField(max_length=30)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'parentescos'
        managed = False
    def __str__(self):
        return self.descripcion.upper()

# ==============================================================================
# CATEGORÍA 3: VIVIENDA, CONTACTOS Y SALUD
# ==============================================================================

class TiposVivienda(models.Model):
    descripcion = models.CharField(max_length=50)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tipos_viviendas'
        managed = False
    def __str__(self):
        return self.descripcion.upper()

class CondicionesVivienda(models.Model):
    descripcion = models.CharField(max_length=50)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'condiciones_viviendas'
        managed = False
    def __str__(self):
        return self.descripcion.upper()

class TipoContacto(models.Model):
    descripcion = models.CharField(max_length=50)
    patron_validacion = models.CharField(max_length=255, null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tipos_contactos'
        managed = False
    def __str__(self):
        return self.descripcion.upper()

class TipoDiscapacidad(models.Model):
    descripcion = models.CharField(max_length=100)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tipos_discapacidades'
        managed = False
    def __str__(self):
        return self.descripcion.upper()

class TipoPatologia(models.Model):
    descripcion = models.CharField(max_length=100)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tipos_patologias'
        managed = False
    def __str__(self):
        return self.descripcion.upper()

# ==============================================================================
# CATEGORÍA 4: FORMACIÓN ACADÉMICA
# ==============================================================================

class NivelesFormacion(models.Model):
    descripcion = models.CharField(max_length=50)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'niveles_formacion'
        managed = False
    def __str__(self):
        return self.descripcion.upper()

class EstatusFormacion(models.Model):
    descripcion = models.CharField(max_length=50)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'estatus_formacion'
        managed = False
    def __str__(self):
        return self.descripcion.upper()

# ==============================================================================
# CATEGORÍA 5: ESTRUCTURA ORGANIZATIVA Y LABORAL
# ==============================================================================

class DireccionSede(models.Model): # Para referenciar en sedes
    class Meta:
        db_table = 'direcciones'
        managed = False

class Sede(models.Model):
    nombre_sede = models.CharField(max_length=100)
    direccion = models.ForeignKey(Direccion, on_delete=models.PROTECT, db_column='direccion_id')
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sedes'
        managed = False
    def __str__(self):
        return self.nombre_sede.upper()

class EstructuraOrganizativa(models.Model):
    nombre_estructura = models.CharField(max_length=150)
    nro_aprobacion = models.CharField(max_length=100, null=True, blank=True)
    fecha_vigencia_desde = models.DateField()
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'estructuras_organizativas'
        managed = False
    def __str__(self):
        return self.nombre_estructura.upper()

class NivelJerarquico(models.Model):
    descripcion = models.CharField(max_length=100) # Ajustado a 100 por el SQL
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'niveles_jerarquicos'
        managed = False
    def __str__(self):
        return self.descripcion.upper()

class TipoUnidad(models.Model):
    descripcion = models.CharField(max_length=100) # Ajustado a 100 por el SQL
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tipos_unidades'
        managed = False
    def __str__(self):
        return self.descripcion.upper()

class UnidadesOrganizativas(models.Model):
    estructura_org = models.ForeignKey(EstructuraOrganizativa, on_delete=models.PROTECT, db_column='estructura_org_id')
    nivel_jerarquico = models.ForeignKey(NivelJerarquico, on_delete=models.PROTECT, db_column='nivel_jerarquico_id')
    tipo_unidad = models.ForeignKey(TipoUnidad, on_delete=models.PROTECT, db_column='tipo_unidad_id')
    unidad_sup = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, db_column='unidad_sup_id')
    
    # 🌟 NUEVO VÍNCULO TERRITORIAL 🌟
    sede = models.ForeignKey('Sede', on_delete=models.PROTECT, db_column='sede_id', null=True, blank=True)
    
    nomenclatura = models.CharField(max_length=20) 
    nombre_unidad = models.CharField(max_length=150)
    esta_activo = models.BooleanField(default=True)
    
    # Auditoría
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'unidades_organizativas'
        managed = False
        
    def __str__(self):
        return self.nombre_unidad.upper()

class CargosGenerico(models.Model):
    nombre_cargo = models.CharField(max_length=100)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cargos_genericos'
        managed = False
    def __str__(self):
        return self.nombre_cargo.upper()

class CargosEstructural(models.Model):
    nombre_cargo_estruct = models.CharField(max_length=100)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cargos_estructurales'
        managed = False
    def __str__(self):
        return self.nombre_cargo_estruct.upper()

class TiposTrabajadore(models.Model):
    descripcion = models.CharField(max_length=50)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tipos_trabajadores'
        managed = False

class EstatusTrabajadore(models.Model):
    descripcion = models.CharField(max_length=50)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'estatus_trabajadores'
        managed = False

# ==============================================================================
# CATEGORÍA 6: RECAUDOS, DOTACIÓN Y SEGURIDAD
# ==============================================================================

class ItemsDotaciones(models.Model):
    nombre_item = models.CharField(max_length=50)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'items_dotaciones'
        managed = False

class TallasDotaciones(models.Model): # <--- AQUÍ ESTÁ LA PIEZA QUE FALTABA
    item_dotacion = models.ForeignKey(ItemsDotaciones, on_delete=models.CASCADE, db_column='item_dotacion_id')
    valor_talla = models.CharField(max_length=10)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tallas_dotaciones'
        managed = False

class TipoRecaudo(models.Model):
    descripcion = models.CharField(max_length=100)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tipos_recaudos'
        managed = False

class Rol(models.Model):
    nombre_rol = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roles'
        managed = False

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
        managed = False

class TipoFormacion(models.Model):
    descripcion = models.CharField(max_length=100)
    esta_activo = models.BooleanField(default=True)
    
    # Campos de auditoría (opcionales para el formulario, pero requeridos por tu BD)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'tipos_formaciones'
        managed = False # Django no intentará crear ni modificar esta tabla
        verbose_name = 'Tipo de Formación'
        verbose_name_plural = 'Tipos de Formaciones'

    def __str__(self):
        return self.descripcion


class Modalidad(models.Model):
    descripcion = models.CharField(max_length=50)
    esta_activo = models.BooleanField(default=True)
    
    # Campos de auditoría
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'modalidades'
        managed = False # Django no intentará crear ni modificar esta tabla
        verbose_name = 'Modalidad'
        verbose_name_plural = 'Modalidades'

    def __str__(self):
        return self.descripcion


# configuracion/models.py

class IdentidadInstitucional(models.Model):
    nombre_oficial = models.CharField(max_length=150) # <-- Antes decía nombre_institucion
    rif = models.CharField(max_length=20)
    direccion_fiscal = models.TextField()
    telefono_contacto = models.CharField(max_length=50, null=True, blank=True)
    correo_contacto = models.CharField(max_length=100, null=True, blank=True)
    ruta_logo_institucional = models.CharField(max_length=255, null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'identidad_institucional'
        managed = False # Django no toca la tabla, solo la lee

class CategoriaPersonal(models.Model):
    descripcion = models.CharField(max_length=100)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categorias_personal'
        managed = False
    def __str__(self):
        return self.descripcion.upper()

class EstatusLaboral(models.Model):
    descripcion = models.CharField(max_length=100)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'estatus_laborales'
        managed = False
    def __str__(self):
        return self.descripcion.upper()