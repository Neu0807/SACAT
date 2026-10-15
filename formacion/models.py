from django.db import models
from django.utils import timezone


# ==============================================================================
# CATÁLOGOS AUXILIARES
# ==============================================================================

class MotivoRechazo(models.Model):
    """Catálogo de motivos para rechazar postulaciones con trazabilidad."""
    descripcion = models.CharField(max_length=200)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'motivos_rechazo'
        managed = False
        verbose_name = 'Motivo de Rechazo'
        verbose_name_plural = 'Motivos de Rechazo'

    def __str__(self):
        return self.descripcion


# ==============================================================================
# OFERTAS DE FORMACIÓN
# ==============================================================================

class OfertaFormacion(models.Model):
    ESTADOS = (
        ('ABIERTA', 'Abierta'),
        ('CERRADA', 'Cerrada'),
        ('FINALIZADA', 'Finalizada'),
        ('CANCELADA', 'Cancelada'),
    )

    tipo_formacion = models.ForeignKey(
        'configuracion.TipoFormacion', on_delete=models.PROTECT,
        db_column='tipo_formacion_id'
    )
    modalidad = models.ForeignKey(
        'configuracion.Modalidad', on_delete=models.PROTECT,
        db_column='modalidad_id'
    )
    institucion = models.CharField(max_length=150)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    horas_academicas = models.IntegerField()
    fecha_publicacion = models.DateField()
    fecha_cierre_postulacion = models.DateField()
    estado_oferta = models.CharField(
        max_length=30, choices=ESTADOS, default='ABIERTA',
        db_column='estado_oferta'
    )
    cupo_maximo_oferta = models.IntegerField(default=50, db_column='cupo_maximo_oferta')
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ofertas_formacion'
        managed = False
        ordering = ['-fecha_publicacion', '-id']

    def __str__(self):
        return self.nombre

    @property
    def cupos_aprobados(self):
        return self.postulaciones.filter(
            estado__in=['APROBADA', 'CONFIRMADO']
        ).count()

    @property
    def cupos_disponibles(self):
        return max(0, (self.cupo_maximo_oferta or 50) - self.cupos_aprobados)

    @property
    def esta_abierta(self):
        return (
            self.estado_oferta == 'ABIERTA'
            and self.esta_activo
            and self.fecha_cierre_postulacion >= timezone.now().date()
        )


# ==============================================================================
# GRUPOS DE OFERTA
# ==============================================================================

class GrupoOferta(models.Model):
    oferta = models.ForeignKey(
        OfertaFormacion, on_delete=models.CASCADE,
        db_column='oferta_id', related_name='grupos'
    )
    nombre_grupo = models.CharField(max_length=50)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    horario = models.CharField(max_length=100, null=True, blank=True)
    lugar = models.CharField(max_length=200, null=True, blank=True)
    instructor = models.CharField(max_length=150, null=True, blank=True)
    cupo_maximo = models.IntegerField(default=20)
    archivo_acta_asistencia = models.CharField(max_length=255, null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'grupos_oferta'
        managed = False
        ordering = ['fecha_inicio', 'id']

    def __str__(self):
        return f"{self.nombre_grupo} - {self.oferta.nombre}"

    @property
    def total_participantes(self):
        return self.participantes.exclude(
            estado__in=['CANCELADA', 'SUSTITUIDO', 'RECHAZADA']
        ).count()


# ==============================================================================
# POSTULACIONES
# ==============================================================================

class Postulacion(models.Model):
    ESTADOS = (
        ('PENDIENTE', 'Pendiente'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
        ('CANCELADA', 'Cancelada'),
        ('CONFIRMADO', 'Confirmado'),
        ('SUSTITUIDO', 'Sustituido'),
    )
    ORIGENES = (
        ('TRABAJADOR', 'Autogestión del Trabajador'),
        ('GESTION_HUMANA', 'Inscripción por GH'),
        ('ASISTENCIA_SITIO', 'Asistencia en sitio'),
    )

    trabajador = models.ForeignKey(
        'trabajadores.Trabajador', on_delete=models.CASCADE,
        db_column='trabajador_id'
    )
    oferta = models.ForeignKey(
        OfertaFormacion, on_delete=models.CASCADE,
        db_column='oferta_id', related_name='postulaciones'
    )
    grupo = models.ForeignKey(
        GrupoOferta, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='grupo_id', related_name='participantes'
    )
    estado = models.CharField(max_length=30, choices=ESTADOS, default='PENDIENTE')
    fecha_postulacion = models.DateTimeField(auto_now_add=True)

    origen_postulacion = models.CharField(
        max_length=30, choices=ORIGENES, default='TRABAJADOR'
    )
    observacion = models.TextField(null=True, blank=True)
    sustituye_a = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        db_column='sustituye_a_id', related_name='sustituido_por'
    )
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)

    motivo_rechazo = models.ForeignKey(
        MotivoRechazo, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='motivo_rechazo_id', related_name='postulaciones'
    )

    # Legacy - mantener por compatibilidad de BD pero no usar
    aprobado_por_jefe = models.ForeignKey(
        'seguridad.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='aprobaciones_jefe', db_column='aprobado_por_jefe'
    )
    fecha_aprobacion_jefe = models.DateTimeField(null=True, blank=True)

    aprobado_por_gh = models.ForeignKey(
        'seguridad.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='aprobaciones_gh', db_column='aprobado_por_gh'
    )
    fecha_aprobacion_gh = models.DateTimeField(null=True, blank=True)

    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'postulaciones'
        managed = False
        ordering = ['-fecha_postulacion']

    def __str__(self):
        return f"{self.trabajador.persona.primer_nombre} → {self.oferta.nombre} ({self.estado})"

    @property
    def puede_cancelar(self):
        """El trabajador puede cancelar solo si está PENDIENTE y la oferta está abierta."""
        return (
            self.estado == 'PENDIENTE'
            and self.oferta.estado_oferta == 'ABIERTA'
            and self.oferta.fecha_cierre_postulacion >= timezone.now().date()
        )

    @property
    def estado_visible_trabajador(self):
        """Estado legible para el trabajador (no muestra jerga interna)."""
        if self.estado == 'PENDIENTE':
            return 'En revisión por Gestión Humana'
        if self.estado == 'APROBADA':
            if self.grupo:
                return f'Convocado - {self.grupo.nombre_grupo}'
            return 'Aprobado - Pendiente asignación de grupo'
        if self.estado == 'RECHAZADA':
            return 'No aprobado'
        if self.estado == 'CANCELADA':
            return 'Cancelada por ti'
        if self.estado == 'CONFIRMADO':
            return f'Convocado - {self.grupo.nombre_grupo if self.grupo else "Sin grupo"}'
        if self.estado == 'SUSTITUIDO':
            return 'Cupo cedido a otro trabajador'
        return self.estado


# ==============================================================================
# ASISTENCIA
# ==============================================================================

class Asistencia(models.Model):
    postulacion = models.ForeignKey(
        Postulacion, on_delete=models.CASCADE,
        db_column='postulacion_id', related_name='asistencias'
    )
    asistio = models.BooleanField(default=False)
    observacion_asistencia = models.TextField(null=True, blank=True)
    archivo_lista = models.CharField(max_length=255, null=True, blank=True)

    # Certificado legacy (se migrará a tabla certificados)
    ruta_certificado = models.CharField(max_length=255, null=True, blank=True)
    fecha_carga_certificado = models.DateTimeField(null=True, blank=True)
    certificado_cargado_por = models.IntegerField(null=True, blank=True)

    fecha_registro = models.DateTimeField(auto_now_add=True)
    esta_activo = models.BooleanField(default=True)
    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'asistencias'
        managed = False

    def __str__(self):
        return f"{self.postulacion.trabajador.persona.primer_nombre} - {'Asistió' if self.asistio else 'No asistió'}"


# ==============================================================================
# CERTIFICADOS (versionado)
# ==============================================================================

class Certificado(models.Model):
    ORIGENES = (
        ('TRABAJADOR', 'Cargado por el Trabajador'),
        ('GH', 'Cargado por Gestión Humana'),
    )

    postulacion = models.ForeignKey(
        Postulacion, on_delete=models.CASCADE,
        db_column='postulacion_id', related_name='certificados'
    )
    ruta_archivo = models.CharField(max_length=255)
    cargado_por = models.IntegerField(null=True, blank=True)
    origen = models.CharField(max_length=20, choices=ORIGENES, default='GH')
    version = models.IntegerField(default=1)
    esta_activo = models.BooleanField(default=True)
    reemplaza_a = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reemplazado_por'
    )
    motivo_reemplazo = models.TextField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)

    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'certificados'
        managed = False
        ordering = ['-version']

    def __str__(self):
        return f"Certificado v{self.version} - {self.postulacion}"


# ==============================================================================
# HISTORIAL DE ESTADOS (auditoría)
# ==============================================================================

class HistorialEstadoPostulacion(models.Model):
    postulacion = models.ForeignKey(
        Postulacion, on_delete=models.CASCADE,
        db_column='postulacion_id', related_name='historial_estados'
    )
    estado_anterior = models.CharField(max_length=30, null=True, blank=True)
    estado_nuevo = models.CharField(max_length=30)
    cambiado_por = models.IntegerField(null=True, blank=True)
    motivo = models.TextField(null=True, blank=True)
    fecha_cambio = models.DateTimeField(auto_now_add=True)

    creado_por = models.IntegerField(null=True, blank=True)
    actualizado_por = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'historial_estados_postulacion'
        managed = False
        ordering = ['-fecha_cambio']