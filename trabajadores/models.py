from django.db import models
# Importamos los modelos maestros de la app configuracion
from configuracion.models import (
    TipoDocIdentificacion, Sexo, EstadoCivil, 
    UnidadesOrganizativas, CargosGenerico, CargosEstructural,
    Direccion, TiposTrabajadore, EstatusTrabajadore
)

# --- MODELO PERSONA (Tabla: personas) ---
class Persona(models.Model):
    tipo_doc_identificacion = models.ForeignKey(TipoDocIdentificacion, on_delete=models.PROTECT, db_column='tipo_doc_identificacion_id')
    cedula = models.CharField(max_length=20, unique=True)
    primer_nombre = models.CharField(max_length=50)
    segundo_nombre = models.CharField(max_length=50, null=True, blank=True)
    primer_apellido = models.CharField(max_length=50)
    segundo_apellido = models.CharField(max_length=50, null=True, blank=True)
    
    # Datos de Nacionalidad y Nacimiento
    es_naturalizado = models.BooleanField(default=False)
    nro_gaceta = models.CharField(max_length=50, null=True, blank=True)
    fecha_gaceta = models.DateField(null=True, blank=True)
    fecha_nacimiento = models.DateField()
    lugar_nacimiento = models.CharField(max_length=150, null=True, blank=True)
    
    sexo = models.ForeignKey(Sexo, on_delete=models.PROTECT, db_column='sexo_id')
    estado_civil = models.ForeignKey(EstadoCivil, on_delete=models.PROTECT, db_column='estado_civil_id')
    esta_activo = models.BooleanField(default=True)
    
    # Auditoría
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'personas'
        managed = False

    def __str__(self):
        return f"{self.primer_nombre} {self.primer_apellido} ({self.cedula})"

# --- RELACIÓN PERSONA-DIRECCIÓN (Tabla: personas_direcciones) ---
class PersonaDireccion(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='persona_id')
    direccion = models.ForeignKey(Direccion, on_delete=models.CASCADE, db_column='direccion_id')
    es_principal = models.BooleanField(default=False)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'personas_direcciones'
        managed = False

# --- MODELO TRABAJADOR (Tabla: trabajadores) ---
class Trabajador(models.Model):
    persona = models.OneToOneField(Persona, on_delete=models.CASCADE, db_column='persona_id')
    unidad_org = models.ForeignKey(UnidadesOrganizativas, on_delete=models.PROTECT, db_column='unidad_org_id')
    cargo_generico = models.ForeignKey(CargosGenerico, on_delete=models.PROTECT, db_column='cargo_generico_id')
    cargo_estructural = models.ForeignKey(CargosEstructural, on_delete=models.PROTECT, db_column='cargo_estructural_id')
    tipo_trabajador = models.ForeignKey(TiposTrabajadore, on_delete=models.PROTECT, db_column='tipo_trabajador_id')
    estatus_trabajador = models.ForeignKey(EstatusTrabajadore, on_delete=models.PROTECT, db_column='estatus_trabajador_id')
    codigo_nomina = models.CharField(max_length=50, unique=True)
    fecha_ingreso_inst = models.DateField()
    esta_activo = models.BooleanField(default=True)
    
    # Auditoría
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trabajadores'
        managed = False