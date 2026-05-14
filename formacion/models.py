from django.db import models


class Expediente(models.Model):
    trabajador = models.ForeignKey('trabajadores.Trabajador', on_delete=models.CASCADE, db_column='trabajador_id')
    tipo_documento_id = models.IntegerField(null=True, blank=True)
    categoria = models.CharField(max_length=50, default='RECAUDO')
    descripcion = models.CharField(max_length=200, null=True, blank=True)
    ruta_archivo = models.CharField(max_length=255)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expediente'
        managed = False


class OfertaFormacion(models.Model):
    tipo_formacion = models.ForeignKey('configuracion.TipoFormacion', on_delete=models.PROTECT, db_column='tipo_formacion_id')
    modalidad = models.ForeignKey('configuracion.Modalidad', on_delete=models.PROTECT, db_column='modalidad_id')
    institucion = models.CharField(max_length=150)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    horas_academicas = models.IntegerField()
    fecha_publicacion = models.DateField()
    fecha_cierre_postulacion = models.DateField()
    estado_oferta = models.CharField(max_length=20, default='ABIERTA', db_column='estado_oferta')
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    cupo_maximo_oferta = models.IntegerField(default=50, db_column='cupo_maximo_oferta')

    class Meta:
        db_table = 'ofertas_formacion'
        managed = False

    def __str__(self):
        return self.nombre


class GrupoOferta(models.Model):
    oferta = models.ForeignKey(OfertaFormacion, on_delete=models.CASCADE, db_column='oferta_id')
    nombre_grupo = models.CharField(max_length=50)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    horario = models.CharField(max_length=50, null=True, blank=True)
    lugar = models.CharField(max_length=200, null=True, blank=True)
    instructor = models.CharField(max_length=150, null=True, blank=True)
    cupo_maximo = models.IntegerField(default=20)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    cupo_maximo = models.IntegerField(default=15)

    class Meta:
        db_table = 'grupos_oferta'
        managed = False


class Postulacion(models.Model):
    trabajador = models.ForeignKey('trabajadores.Trabajador', on_delete=models.CASCADE, db_column='trabajador_id')
    oferta = models.ForeignKey(OfertaFormacion, on_delete=models.CASCADE, db_column='oferta_id', related_name='postulaciones')
    grupo = models.ForeignKey(GrupoOferta, on_delete=models.SET_NULL, null=True, blank=True, db_column='grupo_id')
    estado = models.CharField(max_length=20, default='PENDIENTE')   # ← ESTADO DE LA POSTULACIÓN
    fecha_postulacion = models.DateTimeField(auto_now_add=True)
    aprobado_por_jefe = models.ForeignKey('seguridad.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='aprobaciones_jefe', db_column='aprobado_por_jefe')
    fecha_aprobacion_jefe = models.DateTimeField(null=True, blank=True)
    aprobado_por_gh = models.ForeignKey('seguridad.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='aprobaciones_gh', db_column='aprobado_por_gh')
    fecha_aprobacion_gh = models.DateTimeField(null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'postulaciones'
        managed = False


class Asistencia(models.Model):
    postulacion = models.ForeignKey(Postulacion, on_delete=models.CASCADE, db_column='postulacion_id')
    asistio = models.BooleanField(default=False)
    archivo_lista = models.CharField(max_length=255, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'asistencias'
        managed = False