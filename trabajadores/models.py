from django.db import models

# Importamos lo que sí sabemos que existe en configuracion
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
    
    es_naturalizado = models.BooleanField(default=False)
    nro_gaceta = models.CharField(max_length=50, null=True, blank=True)
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

# --- MODELO VIVIENDA (Tabla: viviendas) ---

# En trabajadores/models.py
class Vivienda(models.Model):
    direccion = models.ForeignKey(Direccion, on_delete=models.CASCADE, db_column='direccion_id')
    tipo_vivienda = models.ForeignKey('configuracion.TiposVivienda', on_delete=models.PROTECT, db_column='tipo_vivienda_id')
    
    # IMPORTANTE: db_column debe ser igualito al nombre que pusiste en el ALTER TABLE
    condicion_vivienda = models.ForeignKey(
        'configuracion.CondicionesVivienda', 
        on_delete=models.PROTECT, 
        db_column='condicion_vivienda_id' 
    )
    
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'viviendas'
        managed = False

# --- RELACIÓN PERSONA-VIVIENDA (Tabla: personas_viviendas) ---
class PersonaVivienda(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='persona_id')
    vivienda = models.ForeignKey(Vivienda, on_delete=models.CASCADE, db_column='vivienda_id')
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'personas_viviendas'
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
    
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trabajadores'
        managed = False

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