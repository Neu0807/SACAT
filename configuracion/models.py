from django.db import models

# ==============================================================================
# CATEGORÍA 1: UBICACIÓN GEOGRÁFICA (Tablas de la Almacenadora)
# ==============================================================================

class Estado(models.Model):
    # id se crea automático por Django al ser SERIAL PRIMARY KEY en SQL
    nombre_estado = models.CharField(max_length=50)
    esta_activo = models.BooleanField(default=True)
    
    # Campos de Auditoría
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'estados'
        managed = False # Muy importante: Django no toca tu tabla real

    def __str__(self):
        return self.nombre_estado


class Municipio(models.Model):
    # Aquí definimos la relación con Estado
    # db_column='estado_id' es vital para que coincida con tu SQL
    estado = models.ForeignKey(
        Estado, 
        on_delete=models.CASCADE, 
        db_column='estado_id', 
        related_name='municipios'
    )
    nombre_municipio = models.CharField(max_length=100)
    esta_activo = models.BooleanField(default=True)
    
    # Auditoría
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'municipios'
        managed = False

    def __str__(self):
        return f"{self.nombre_municipio} - {self.estado.nombre_estado}"


class Parroquia(models.Model):
    # Relación con Municipio
    municipio = models.ForeignKey(
        Municipio, 
        on_delete=models.CASCADE, 
        db_column='municipio_id', 
        related_name='parroquias'
    )
    nombre_parroquia = models.CharField(max_length=100)
    esta_activo = models.BooleanField(default=True)
    
    # Auditoría
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'parroquias'
        managed = False

    def __str__(self):
        return f"{self.nombre_parroquia} ({self.municipio.nombre_municipio})"
    
# ==============================================================================
# CATEGORÍA 2: IDENTIFICACIÓN (Tablas maestras)
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
        return self.descripcion

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
        return self.descripcion

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
        return self.descripcion