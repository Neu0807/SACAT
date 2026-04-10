import os
from django.db import models
from configuracion.models import (
    TipoDocIdentificacion, Sexo, EstadoCivil, 
    Estado, Municipio, Parroquia, Direccion, TipoContacto,
    TiposVivienda, CondicionesVivienda, CentroVotacion,
    TipoDiscapacidad, TipoPatologia, NivelesFormacion, 
    EstatusFormacion, UnidadesOrganizativas, CargosGenerico, 
    CargosEstructural, TiposTrabajadore, EstatusTrabajadore,
    Parentesco, TipoRecaudo, TallasDotaciones,
    TipoFormacion, Modalidad 
)

# ==============================================================================
# MÓDULO DE IDENTIDAD (LA PERSONA) - PASO 1
# ==============================================================================

class Persona(models.Model):
    tipo_doc_identificacion = models.ForeignKey(TipoDocIdentificacion, on_delete=models.PROTECT, db_column='tipo_doc_identificacion_id')
    cedula = models.CharField(max_length=20, unique=True)
    
    # 🌟 CAMPOS DE IDENTIDAD 🌟
    rif = models.CharField(max_length=20, unique=True, null=True, blank=True)
    fecha_vencimiento_cedula = models.DateField(null=True, blank=True)
    fecha_vencimiento_rif = models.DateField(null=True, blank=True)
    
    primer_nombre = models.CharField(max_length=50)
    segundo_nombre = models.CharField(max_length=50, null=True, blank=True)
    primer_apellido = models.CharField(max_length=50)
    segundo_apellido = models.CharField(max_length=50, null=True, blank=True)
    
    # Bloque de Naturalización
    es_naturalizado = models.BooleanField(default=False)
    nro_gaceta = models.CharField(max_length=50, null=True, blank=True)
    
    # 🌟 NUEVO CAMPO AGREGADO 🌟
    es_extraordinaria = models.BooleanField(default=False)
    
    fecha_gaceta = models.DateField(null=True, blank=True)
    fecha_nacimiento = models.DateField()
    lugar_nacimiento = models.CharField(max_length=150, null=True, blank=True)
    sexo = models.ForeignKey(Sexo, on_delete=models.PROTECT, db_column='sexo_id')
    estado_civil = models.ForeignKey(EstadoCivil, on_delete=models.PROTECT, db_column='estado_civil_id')
    
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'personas'
        managed = False

    def __str__(self):
        return f"{self.primer_nombre} {self.primer_apellido} ({self.cedula})"


# ==============================================================================
# MÓDULO DE UBICACIÓN Y VIVIENDA - PASO 2
# ==============================================================================

class PersonaDireccion(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='persona_id')
    direccion = models.ForeignKey(Direccion, on_delete=models.CASCADE, db_column='direccion_id')
    es_principal = models.BooleanField(default=False)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'personas_direcciones'
        managed = False

# Busca la clase Vivienda y déjala así:
class Vivienda(models.Model):
    direccion = models.ForeignKey(Direccion, on_delete=models.CASCADE, db_column='direccion_id')
    tipo_vivienda = models.ForeignKey(TiposVivienda, on_delete=models.PROTECT, db_column='tipo_vivienda_id')
    # AGREGA ESTA LÍNEA QUE FALTA:
    condicion_vivienda = models.ForeignKey(CondicionesVivienda, on_delete=models.PROTECT, db_column='condicion_vivienda_id')
    
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'viviendas'
        managed = False

class PersonaVivienda(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='persona_id')
    vivienda = models.ForeignKey(Vivienda, on_delete=models.CASCADE, db_column='vivienda_id')
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'personas_viviendas'
        managed = False

class DatosElectorales(models.Model):
    persona = models.OneToOneField(Persona, on_delete=models.CASCADE, db_column='persona_id')
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.PROTECT, db_column='centro_votacion_id')
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'datos_electorales'
        managed = False


# ==============================================================================
# MÓDULO DE CONTACTOS - PASO 3
# ==============================================================================

class ContactoPersonal(models.Model):
    tipo_contacto = models.ForeignKey(TipoContacto, on_delete=models.PROTECT, db_column='tipo_contacto_id')
    valor_contacto = models.CharField(max_length=150, unique=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contactos_personales'
        managed = False

class PersonaContactoPersonal(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='persona_id')
    contacto_personal = models.ForeignKey(ContactoPersonal, on_delete=models.CASCADE, db_column='contacto_personal_id')
    es_principal = models.BooleanField(default=False)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'personas_contactos_personales'
        managed = False

class ContactoEmergencia(models.Model):
    primer_nombre = models.CharField(max_length=50)
    segundo_nombre = models.CharField(max_length=50, null=True, blank=True)
    primer_apellido = models.CharField(max_length=50)
    segundo_apellido = models.CharField(max_length=50, null=True, blank=True)
    telefono = models.CharField(max_length=50)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contactos_emergencia'
        managed = False

class PersonaContactoEmergencia(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='persona_id')
    contacto_emergencia = models.ForeignKey(ContactoEmergencia, on_delete=models.CASCADE, db_column='contacto_emergencia_id')
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'personas_contactos_emergencia'
        managed = False


# ==============================================================================
# MÓDULO DE FORMACIÓN - PASOS 4 Y 5
# ==============================================================================

class FormacionAcademica(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='persona_id')
    nivel_formacion = models.ForeignKey(NivelesFormacion, on_delete=models.PROTECT, db_column='nivel_formacion_id')
    estatus_formacion = models.ForeignKey(EstatusFormacion, on_delete=models.PROTECT, db_column='estatus_formacion_id')
    institucion = models.CharField(max_length=150)
    especialidad = models.CharField(max_length=150, null=True, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'formaciones_academicas'
        managed = False

# Nota: Si no las tienes importadas arriba, asegúrate de importar las tablas catálogo
# from configuracion.models import TipoFormacion, Modalidad

class FormacionAdicional(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='persona_id')
    
    # 🌟 AQUI ESTÁN LAS DOS RELACIONES NUEVAS 🌟
    tipo_formacion = models.ForeignKey('configuracion.TipoFormacion', on_delete=models.PROTECT, db_column='tipo_formacion_id', null=True, blank=True)
    modalidad = models.ForeignKey('configuracion.Modalidad', on_delete=models.PROTECT, db_column='modalidad_id', null=True, blank=True)
    
    # El resto de tus campos intactos
    nombre_formacion_ad = models.CharField(max_length=150)
    institucion = models.CharField(max_length=150)
    duracion_horas = models.IntegerField(null=True, blank=True)
    fecha_culminacion = models.DateField(null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'formaciones_adicionales'
        managed = False


# ==============================================================================
# MÓDULO DE SALUD - PASO 6
# ==============================================================================

class PersonaSalud(models.Model):
    persona = models.OneToOneField(Persona, on_delete=models.CASCADE, db_column='persona_id')
    tipo_discapacidad = models.ForeignKey(TipoDiscapacidad, on_delete=models.PROTECT, db_column='tipo_discapacidad_id', null=True, blank=True)
    nro_conapdis = models.CharField(max_length=50, null=True, blank=True)
    tipo_sangre = models.CharField(max_length=5, null=True, blank=True)
    alergias = models.TextField(null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'personas_salud'
        managed = False

class PersonaPatologia(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='persona_id')
    tipo_patologia = models.ForeignKey(TipoPatologia, on_delete=models.PROTECT, db_column='tipo_patologia_id')
    descripcion_adicional = models.TextField(null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'personas_patologias'
        managed = False


# ==============================================================================
# MÓDULO DE CARGA FAMILIAR - PASO 7
# ==============================================================================

class CargaFamiliar(models.Model):
    cedula = models.CharField(max_length=20, unique=True, null=True, blank=True)
    primer_nombre = models.CharField(max_length=50)
    segundo_nombre = models.CharField(max_length=50, null=True, blank=True)
    primer_apellido = models.CharField(max_length=50)
    segundo_apellido = models.CharField(max_length=50, null=True, blank=True)
    sexo = models.ForeignKey(Sexo, on_delete=models.PROTECT, db_column='sexo_id')
    fecha_nacimiento = models.DateField()
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cargas_familiares'
        managed = False

class PersonaCargaFamiliar(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='persona_id')
    carga_familiar = models.ForeignKey(CargaFamiliar, on_delete=models.CASCADE, db_column='carga_familiar_id')
    parentesco = models.ForeignKey(Parentesco, on_delete=models.PROTECT, db_column='parentesco_id')
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'personas_cargas_familiares'
        managed = False


# ==============================================================================
# MÓDULO LABORAL (EL TRABAJADOR) - PASO 8
# ==============================================================================

class Trabajador(models.Model):
    persona = models.OneToOneField('Persona', on_delete=models.CASCADE, db_column='persona_id')
    
    # Ubicación y Clasificación
    sede = models.ForeignKey('configuracion.Sede', on_delete=models.PROTECT, db_column='sede_id')
    nivel_jerarquico = models.ForeignKey('configuracion.NivelJerarquico', on_delete=models.PROTECT, db_column='nivel_jerarquico_id')
    unidad_org = models.ForeignKey('configuracion.UnidadesOrganizativas', on_delete=models.PROTECT, db_column='unidad_org_id')
    tipo_trabajador = models.ForeignKey('configuracion.TiposTrabajadore', on_delete=models.PROTECT, db_column='tipo_trabajador_id')
    categoria = models.ForeignKey('configuracion.CategoriaPersonal', on_delete=models.PROTECT, db_column='categoria_id')
    cargo_generico = models.ForeignKey('configuracion.CargosGenerico', on_delete=models.PROTECT, db_column='cargo_generico_id')
    cargo_estructural = models.ForeignKey('configuracion.CargosEstructural', on_delete=models.PROTECT, db_column='cargo_estructural_id')
    
    codigo_nomina = models.CharField(max_length=50, unique=True)
    fecha_ingreso_inst = models.DateField()
    
    # 🌟 CONTROL DE FASES SACAT 🌟
    fase_actual = models.IntegerField(default=1) # 1: Registro Inicial (RRHH), 2: Completación (Trabajador)
    registro_completado = models.BooleanField(default=False)

    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trabajadores'
        managed = False

    def __str__(self):
        return f"{self.persona.primer_nombre} {self.persona.primer_apellido} - {self.codigo_nomina}"

class ExperienciaPrevia(models.Model):
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, db_column='trabajador_id')
    empresa = models.CharField(max_length=150)
    cargo = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'experiencias_previas'
        managed = False

class Dotacion(models.Model):
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, db_column='trabajador_id')
    talla_dotacion = models.ForeignKey(TallasDotaciones, on_delete=models.PROTECT, db_column='talla_dotacion_id')
    fecha_entrega = models.DateField()
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dotaciones'
        managed = False

class ContactoInstitucional(models.Model):
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, db_column='trabajador_id')
    correo_corp = models.EmailField(max_length=150, null=True, blank=True)
    ext_oficina = models.CharField(max_length=20, null=True, blank=True)
    telefono_corp = models.CharField(max_length=50, null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contactos_institucionales'
        managed = False


# ==============================================================================
# MÓDULO DE RECAUDOS Y AUDITORÍA - PASO 9
# ==============================================================================


# Función para organizar archivos: media/recaudos/trabajador_ID/nombre_archivo.pdf
# trabajadores/models.py

def ruta_recaudos_trabajador(instance, filename):
    """
    Renombrado automático: di_32556836.pdf
    """
    # Obtenemos la cédula desde la relación
    cedula = instance.trabajador.persona.cedula
    # Extraemos la extensión original (.pdf, .png, etc.)
    extension = os.path.splitext(filename)[1].lower()
    # Retornamos la ruta final: di_CEDULA.extension
    return f'recaudos/trabajador_{cedula}/di_{cedula}{extension}'

class Recaudo(models.Model):
    trabajador = models.ForeignKey('Trabajador', on_delete=models.CASCADE, db_column='trabajador_id')
    tipo_recaudo = models.ForeignKey('configuracion.TipoRecaudo', on_delete=models.PROTECT, db_column='tipo_recaudo_id')
    
    # Cambiado a FileField para que Django gestione la subida física
    ruta_archivo = models.FileField(upload_to=ruta_recaudos_trabajador, max_length=255)
    
    fecha_vencimiento = models.DateField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recaudos'
        managed = False  # Mantenemos managed=False para no chocar con tu SQL

class Auditoria(models.Model):
    usuario_id = models.IntegerField() # Referencia manual al ID de la tabla usuarios
    accion = models.CharField(max_length=50)
    tabla_afectada = models.CharField(max_length=100)
    registro_id = models.IntegerField(null=True, blank=True)
    ip_conexion = models.CharField(max_length=45, null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'auditorias'
        managed = False