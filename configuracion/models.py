from django.db import models

# ==============================================================================
# CATEGORÍA 1: UBICACIÓN GEOGRÁFICA (Tablas de la Almacenadora)
# ==============================================================================

class Estado(models.Model):
    nombre_estado = models.CharField(max_length=50)
    esta_activo = models.BooleanField(default=True)
    
    # Campos de Auditoría
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'estados'
        managed = False 

    def save(self, *args, **kwargs):
        if self.nombre_estado:
            self.nombre_estado = self.nombre_estado.strip().upper()
        super(Estado, self).save(*args, **kwargs)

    def __str__(self):
        return self.nombre_estado


class Municipio(models.Model):
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

    def save(self, *args, **kwargs):
        if self.nombre_municipio:
            self.nombre_municipio = self.nombre_municipio.strip().upper()
        super(Municipio, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre_municipio} - {self.estado.nombre_estado}"


class Parroquia(models.Model):
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

    def save(self, *args, **kwargs):
        if self.nombre_parroquia:
            self.nombre_parroquia = self.nombre_parroquia.strip().upper()
        super(Parroquia, self).save(*args, **kwargs)

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

    def save(self, *args, **kwargs):
        if self.sigla: self.sigla = self.sigla.strip().upper()
        if self.descripcion: self.descripcion = self.descripcion.strip().upper()
        if self.ente_emisor: self.ente_emisor = self.ente_emisor.strip().upper()
        if self.aplica_a: self.aplica_a = self.aplica_a.strip().upper()
        super(TipoDocIdentificacion, self).save(*args, **kwargs)

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

    def save(self, *args, **kwargs):
        if self.sigla: self.sigla = self.sigla.strip().upper()
        if self.descripcion: self.descripcion = self.descripcion.strip().upper()
        super(Sexo, self).save(*args, **kwargs)

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

    def save(self, *args, **kwargs):
        if self.sigla: self.sigla = self.sigla.strip().upper()
        if self.descripcion: self.descripcion = self.descripcion.strip().upper()
        super(EstadoCivil, self).save(*args, **kwargs)

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

    def save(self, *args, **kwargs):
        if self.descripcion: self.descripcion = self.descripcion.strip().upper()
        super(TipoContacto, self).save(*args, **kwargs)

    def __str__(self):
        return self.descripcion