import os
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.core.files.storage import FileSystemStorage
from django.contrib import messages

# Decorador personalizado de permisos
from seguridad.decorators import permiso_requerido

# Modelos de formación
from .models import (
    OfertaFormacion, Postulacion, GrupoOferta, Asistencia,
    Certificado, MotivoRechazo, HistorialEstadoPostulacion,
)

# Modelos de catálogo
from configuracion.models import TipoFormacion, Modalidad, UnidadesOrganizativas, IdentidadInstitucional

# Modelos de trabajador
from trabajadores.models import Trabajador, FormacionAdicional, Recaudo


def _es_admin_prueba(user):
    """Determina si el usuario es Superusuario o Administrador para permitir editar fecha_publicacion."""
    if getattr(user, 'es_superusuario', False) or getattr(user, 'is_superuser', False):
        return True
    rol_nombre = user.rol.nombre_rol.upper() if getattr(user, 'rol', None) else ''
    return 'ADMIN' in rol_nombre or 'SUPER' in rol_nombre


def _actualizar_cierres_vencidos():
    """Cierra automáticamente las ofertas cuya fecha de cierre ya pasó."""
    hoy = timezone.now().date()
    OfertaFormacion.objects.filter(
        estado_oferta='ABIERTA',
        fecha_cierre_postulacion__lt=hoy,
        esta_activo=True
    ).update(estado_oferta='CERRADA')


# =============================================================================
# 1. CENTRO DE OPERACIONES: OFERTAS Y WORKSPACE (GESTIÓN HUMANA)
# =============================================================================

@login_required
@permiso_requerido('ver_ofertas_formacion')
def listar_ofertas(request):
    """Tablero Maestro de Gestión Humana con KPIs globales y acceso al Workspace de cada curso."""
    _actualizar_cierres_vencidos()

    ofertas = OfertaFormacion.objects.select_related('tipo_formacion', 'modalidad').annotate(
        total_postulados=Count('postulaciones', filter=~Q(postulaciones__estado='CANCELADA')),
        pendientes_count=Count('postulaciones', filter=Q(postulaciones__estado='PENDIENTE')),
        aprobados_count=Count('postulaciones', filter=Q(postulaciones__estado__in=['APROBADA', 'APROBADO_GH', 'CONFIRMADO'])),
        grupos_count=Count('grupos', filter=Q(grupos__esta_activo=True), distinct=True)
    ).order_by('-fecha_publicacion', '-id')

    kpis = {
        'ofertas_activas': OfertaFormacion.objects.filter(estado_oferta='ABIERTA', esta_activo=True).count(),
        'pendientes_totales': Postulacion.objects.filter(estado='PENDIENTE', oferta__esta_activo=True).count(),
        'aprobados_totales': Postulacion.objects.filter(estado__in=['APROBADA', 'APROBADO_GH', 'CONFIRMADO']).count(),
        'certificados_emitidos': Asistencia.objects.filter(asistio=True).exclude(ruta_certificado__isnull=True).exclude(ruta_certificado='').count(),
    }

    tipos = TipoFormacion.objects.filter(esta_activo=True).order_by('descripcion')
    modalidades = Modalidad.objects.filter(esta_activo=True).order_by('descripcion')

    return render(request, 'formacion/gestion_humana/panel_gestion.html', {
        'ofertas': ofertas,
        'kpis': kpis,
        'tipos': tipos,
        'modalidades': modalidades,
        'puede_editar_fecha_pub': _es_admin_prueba(request.user),
    })


@login_required
@permiso_requerido('crear_oferta')
def crear_oferta(request):
    """Crear una nueva oferta de formación."""
    puede_editar_fecha_pub = _es_admin_prueba(request.user)
    hoy = timezone.now().date()

    if request.method == 'POST':
        try:
            fecha_pub = request.POST.get('fecha_publicacion') if puede_editar_fecha_pub else hoy
            if not fecha_pub:
                fecha_pub = hoy

            cupo = int(request.POST.get('cupo_maximo_oferta', 50))
            OfertaFormacion.objects.create(
                tipo_formacion_id=request.POST.get('tipo_formacion_id'),
                modalidad_id=request.POST.get('modalidad_id'),
                institucion=request.POST.get('institucion', '').strip().upper(),
                nombre=request.POST.get('nombre', '').strip().upper(),
                descripcion=request.POST.get('descripcion', '').strip(),
                horas_academicas=request.POST.get('horas_academicas'),
                cupo_maximo_oferta=cupo,
                fecha_publicacion=fecha_pub,
                fecha_cierre_postulacion=request.POST.get('fecha_cierre_postulacion'),
                estado_oferta='ABIERTA',
                creado_por=request.user.id,
                actualizado_por=request.user.id,
            )
            return JsonResponse({'success': True, 'mensaje': 'Oferta de formación creada exitosamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    tipos = TipoFormacion.objects.filter(esta_activo=True)
    modalidades = Modalidad.objects.filter(esta_activo=True)
    return render(request, 'ofertas/crear_oferta.html', {
        'tipos': tipos,
        'modalidades': modalidades,
        'hoy': hoy.strftime('%Y-%m-%d'),
        'puede_editar_fecha_pub': puede_editar_fecha_pub,
    })


@login_required
@permiso_requerido('editar_oferta')
def editar_oferta(request, oferta_id):
    """Editar una oferta de formación existente."""
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    puede_editar_fecha_pub = _es_admin_prueba(request.user)

    if request.method == 'POST':
        try:
            oferta.tipo_formacion_id = request.POST.get('tipo_formacion_id')
            oferta.modalidad_id = request.POST.get('modalidad_id')
            oferta.institucion = request.POST.get('institucion', '').strip().upper()
            oferta.nombre = request.POST.get('nombre', '').strip().upper()
            oferta.descripcion = request.POST.get('descripcion', '').strip()
            oferta.horas_academicas = request.POST.get('horas_academicas')
            oferta.cupo_maximo_oferta = int(request.POST.get('cupo_maximo_oferta', oferta.cupo_maximo_oferta or 50))
            if puede_editar_fecha_pub and request.POST.get('fecha_publicacion'):
                oferta.fecha_publicacion = request.POST.get('fecha_publicacion')
            oferta.fecha_cierre_postulacion = request.POST.get('fecha_cierre_postulacion')
            if request.POST.get('estado_oferta'):
                oferta.estado_oferta = request.POST.get('estado_oferta')
            oferta.actualizado_por = request.user.id
            oferta.save()
            return JsonResponse({'success': True, 'mensaje': 'Oferta actualizada correctamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    tipos = TipoFormacion.objects.filter(esta_activo=True)
    modalidades = Modalidad.objects.filter(esta_activo=True)
    return render(request, 'ofertas/editar_oferta.html', {
        'oferta': oferta,
        'tipos': tipos,
        'modalidades': modalidades,
        'puede_editar_fecha_pub': puede_editar_fecha_pub,
    })


@login_required
@permiso_requerido('inhabilitar_oferta')
@require_POST
def toggle_oferta(request, oferta_id):
    """Activar o inhabilitar una oferta de formación."""
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    oferta.esta_activo = not oferta.esta_activo
    oferta.actualizado_por = request.user.id
    oferta.save()
    estado = "habilitada" if oferta.esta_activo else "inhabilitada"
    return JsonResponse({'success': True, 'mensaje': f'Oferta {estado}.'})


@login_required
@permiso_requerido('editar_oferta')
@require_POST
def cambiar_estado_oferta(request, oferta_id):
    """Permite a GH cambiar manualmente el estado de una oferta."""
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    nuevo_estado = request.POST.get('estado_oferta', '').strip().upper()
    if nuevo_estado not in ['ABIERTA', 'CERRADA', 'FINALIZADA', 'CANCELADA']:
        return JsonResponse({'success': False, 'error': 'Estado no válido.'})
    oferta.estado_oferta = nuevo_estado
    oferta.actualizado_por = request.user.id
    oferta.save()
    return JsonResponse({'success': True, 'mensaje': f'El estado de la oferta pasó a {nuevo_estado}.'})


# =============================================================================
# 2. PORTAL DE CAPACITACIÓN (TRABAJADOR)
# =============================================================================

@login_required
@permiso_requerido('ver_ofertas_activas')
def listar_ofertas_activas(request):
    """Portal Unificado del Trabajador para autogestión y postulaciones."""
    _actualizar_cierres_vencidos()
    
    cedula_usuario = getattr(request.user, 'nombre_usuario', None) or getattr(request.user, 'username', '')
    trabajador = Trabajador.objects.filter(persona__cedula=cedula_usuario, esta_activo=True).first()
    
    if not trabajador:
        messages.warning(request, "Tu usuario no posee un expediente de trabajador asociado para ingresar al portal.")
        return redirect('formacion:listar_ofertas')

    ofertas_abiertas = OfertaFormacion.objects.filter(
        estado_oferta='ABIERTA',
        esta_activo=True
    ).select_related('tipo_formacion', 'modalidad').order_by('-fecha_publicacion', '-id')

    mis_postulaciones_qs = Postulacion.objects.filter(
        trabajador=trabajador
    ).select_related(
        'oferta__tipo_formacion', 'oferta__modalidad', 'grupo', 'sustituye_a__trabajador__persona'
    ).prefetch_related('asistencias').order_by('-fecha_postulacion')

    mapa_postulaciones = {}
    for p in mis_postulaciones_qs:
        asist = p.asistencias.first()
        p.registro_asistencia = asist
        if p.estado != 'CANCELADA':
            mapa_postulaciones[p.oferta_id] = p

    ofertas_portal = []
    for o in ofertas_abiertas:
        aprobados_actuales = Postulacion.objects.filter(
            oferta=o, estado__in=['APROBADA', 'APROBADO_GH', 'CONFIRMADO']
        ).count()
        cupo_max = o.cupo_maximo_oferta or 50
        
        # Guardamos en un atributo dinámico con otro nombre para evitar el conflicto del setter
        o.calculated_cupos_disponibles = max(0, cupo_max - aprobados_actuales)
        o.mi_postulacion = mapa_postulaciones.get(o.id)
        ofertas_portal.append(o)

    tab_activa = request.GET.get('tab', 'ofertas')

    # Detección segura de rol GH / Admin para pruebas cruzadas en el portal
    rol_nombre = request.user.rol.nombre_rol.upper() if getattr(request.user, 'rol', None) else ''
    es_personal_gh = any(p in rol_nombre for p in ['GESTION', 'ADMINISTRADOR', 'SUPERUSUARIO', 'HUMANA']) or _es_admin_prueba(request.user)

    return render(request, 'formacion/trabajador/portal_capacitacion.html', {
        'ofertas_activas': ofertas_portal,
        'mis_postulaciones': mis_postulaciones_qs,
        'active_tab': tab_activa,
        'es_personal_gh': es_personal_gh,
    })


@login_required
@permiso_requerido('ver_ofertas_activas')
def detalle_oferta_trabajador(request, oferta_id):
    """Devuelve el contenido del Modal 'Ver Detalle' para el trabajador."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    oferta = get_object_or_404(
        OfertaFormacion.objects.select_related('tipo_formacion', 'modalidad'),
        id=oferta_id, esta_activo=True
    )

    aprobados_actuales = Postulacion.objects.filter(
        oferta=oferta, estado__in=['APROBADA', 'APROBADO_GH', 'CONFIRMADO']
    ).count()
    cupo_max = oferta.cupo_maximo_oferta or 50
    cupos_disponibles = max(0, cupo_max - aprobados_actuales)

    mi_postulacion = Postulacion.objects.filter(
        trabajador=trabajador, oferta=oferta
    ).exclude(estado='CANCELADA').first()

    return render(request, 'postulaciones/detalle_oferta_modal.html', {
        'oferta': oferta,
        'cupos_disponibles': cupos_disponibles,
        'mi_postulacion': mi_postulacion,
    })


@login_required
@permiso_requerido('postular_oferta')
@require_POST
def postular_oferta(request, oferta_id):
    """El trabajador confirma su postulación."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id, estado_oferta='ABIERTA', esta_activo=True)

    hoy = timezone.now().date()
    if oferta.fecha_cierre_postulacion and oferta.fecha_cierre_postulacion < hoy:
        return JsonResponse({'success': False, 'error': 'El período de postulación para esta oferta ya cerró.'})

    existente = Postulacion.objects.filter(trabajador=trabajador, oferta=oferta).first()
    if existente:
        if existente.estado == 'CANCELADA':
            existente.estado = 'PENDIENTE'
            existente.fecha_postulacion = timezone.now()
            existente.fecha_cancelacion = None
            existente.observacion = 'Postulación reactivada por el trabajador.'
            existente.actualizado_por = request.user.id
            existente.save()
            return JsonResponse({'success': True, 'mensaje': 'Tu postulación ha sido reactivada exitosamente.'})
        return JsonResponse({'success': False, 'error': f'Ya posees una postulación activa en estado {existente.estado}.'})

    Postulacion.objects.create(
        trabajador=trabajador,
        oferta=oferta,
        estado='PENDIENTE',
        origen_postulacion='TRABAJADOR',
        creado_por=request.user.id,
        actualizado_por=request.user.id,
    )
    return JsonResponse({'success': True, 'mensaje': 'Te has postulado exitosamente. Gestión Humana revisará tu solicitud.'})


@login_required
@permiso_requerido('postular_oferta')
@require_POST
def cancelar_postulacion(request, postulacion_id):
    """Permite al trabajador cancelar su postulación usando mensajes de Django para SweetAlert2."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    postulacion = get_object_or_404(Postulacion.objects.select_related('oferta'), id=postulacion_id, trabajador=trabajador)

    if postulacion.oferta.estado_oferta != 'ABIERTA':
        messages.error(request, 'No puedes cancelar esta postulación porque la oferta ya cerró.')
        return redirect('/formacion/portal/?tab=historial')

    if postulacion.estado not in ['PENDIENTE', 'APROBADA', 'APROBADO_GH']:
        messages.error(request, f'No es posible cancelar una postulación en estado {postulacion.estado}.')
        return redirect('/formacion/portal/?tab=historial')

    motivo = request.POST.get('motivo', '').strip() or 'Cancelada voluntariamente por el trabajador antes del cierre.'
    postulacion.estado = 'CANCELADA'
    postulacion.grupo = None
    postulacion.fecha_cancelacion = timezone.now()
    postulacion.observacion = motivo
    postulacion.actualizado_por = request.user.id
    postulacion.save()

    messages.success(request, 'Tu postulación ha sido cancelada correctamente.')
    return redirect('/formacion/portal/?tab=historial')


@login_required
@permiso_requerido('ver_mis_postulaciones')
def listar_postulaciones(request):
    return redirect('/formacion/postulaciones/?tab=historial')


# =============================================================================
# 3. PESTAÑA 1 DEL WORKSPACE GH: APROBACIÓN, RECHAZO, INSCRIPCIÓN Y SUSTITUCIÓN (JSON)
# =============================================================================

@login_required
def bandeja_aprobacion(request):
    return redirect('listar_ofertas')


@login_required
@permiso_requerido('ver_ofertas_formacion')
def workspace_postulaciones(request, oferta_id):
    """Carga la Pestaña de Postulaciones y Aprobación para Gestión Humana."""
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    postulaciones = Postulacion.objects.filter(
        oferta=oferta
    ).select_related(
        'trabajador__persona',
        'trabajador__unidad_org',
        'trabajador__cargo_estructural',
        'grupo',
        'sustituye_a__trabajador__persona'
    ).order_by('-fecha_postulacion')

    unidades = UnidadesOrganizativas.objects.filter(esta_activo=True).order_by('nombre_unidad')

    ids_inscritos = postulaciones.exclude(estado__in=['CANCELADA', 'SUSTITUIDO', 'RECHAZADA']).values_list('trabajador_id', flat=True)
    trabajadores_disponibles = Trabajador.objects.filter(
        esta_activo=True
    ).exclude(id__in=ids_inscritos).select_related('persona', 'unidad_org', 'cargo_estructural').order_by('persona__primer_nombre')

    aprobados = postulaciones.filter(estado__in=['APROBADA', 'APROBADO_GH', 'CONFIRMADO']).count()
    pendientes = postulaciones.filter(estado='PENDIENTE').count()
    rechazados = postulaciones.filter(estado__in=['RECHAZADA', 'RECHAZADO_GH']).count()
    cupo_max = oferta.cupo_maximo_oferta or 50

    motivos_rechazo = MotivoRechazo.objects.filter(esta_activo=True).order_by('id')

    return render(request, 'formacion/gestion_humana/workspace_postulaciones.html', {
        'oferta': oferta,
        'postulaciones': postulaciones,
        'unidades': unidades,
        'trabajadores_disponibles': trabajadores_disponibles,
        'motivos_rechazo': motivos_rechazo,
        'metricas': {
            'cupo_max': cupo_max,
            'aprobados': aprobados,
            'pendientes': pendientes,
            'rechazados': rechazados,
            'disponibles': max(0, cupo_max - aprobados),
        }
    })


@login_required
@permiso_requerido('aprobar_gh')
@require_POST
@transaction.atomic
def aprobar_gh(request, postulacion_id):
    """GH aprueba una postulación de manera individual validando el cupo global."""
    postulacion = get_object_or_404(Postulacion.objects.select_related('oferta'), id=postulacion_id)
    oferta = postulacion.oferta

    if postulacion.estado != 'PENDIENTE':
        return JsonResponse({'success': False, 'error': 'La postulación ya no se encuentra en estado pendiente.'})

    aprobados_actuales = Postulacion.objects.filter(
        oferta=oferta, estado__in=['APROBADA', 'APROBADO_GH', 'CONFIRMADO']
    ).count()
    if aprobados_actuales >= (oferta.cupo_maximo_oferta or 50):
        return JsonResponse({'success': False, 'error': 'Se alcanzó el cupo máximo de aprobados para esta oferta.'})

    estado_anterior = postulacion.estado
    postulacion.estado = 'APROBADA'
    postulacion.aprobado_por_gh = request.user
    postulacion.fecha_aprobacion_gh = timezone.now()
    postulacion.observacion = 'Aprobada por Gestión Humana.'
    postulacion.actualizado_por = request.user.id
    postulacion.save()

    HistorialEstadoPostulacion.objects.create(
        postulacion=postulacion,
        estado_anterior=estado_anterior,
        estado_nuevo='APROBADA',
        cambiado_por=request.user.id,
        motivo="Aprobado por Gestión Humana"
    )

    return JsonResponse({'success': True, 'mensaje': 'Postulación aprobada correctamente.'})


@login_required
@permiso_requerido('aprobar_gh')
@require_POST
@transaction.atomic
def aprobar_masivo_gh(request, oferta_id):
    """Aprueba en lote múltiples postulaciones seleccionadas."""
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    ids = request.POST.getlist('postulaciones_ids[]') or request.POST.getlist('postulacion_ids')
    if not ids:
        return JsonResponse({'success': False, 'error': 'Seleccione al menos una postulación.'})

    aprobados_actuales = Postulacion.objects.filter(
        oferta=oferta, estado__in=['APROBADA', 'APROBADO_GH', 'CONFIRMADO']
    ).count()
    cupos_restantes = (oferta.cupo_maximo_oferta or 50) - aprobados_actuales
    if len(ids) > cupos_restantes:
        return JsonResponse({'success': False, 'error': f'Solo quedan {cupos_restantes} cupos disponibles.'})

    actualizados = Postulacion.objects.filter(
        id__in=ids, oferta=oferta, estado='PENDIENTE'
    ).update(
        estado='APROBADA',
        aprobado_por_gh=request.user,
        fecha_aprobacion_gh=timezone.now(),
        observacion='Aprobación masiva por Gestión Humana.',
        actualizado_por=request.user.id
    )
    return JsonResponse({'success': True, 'mensaje': f'Se aprobaron {actualizados} postulaciones exitosamente.'})


@login_required
@permiso_requerido('rechazar_gh')
@require_POST
@transaction.atomic
def rechazar_gh(request, postulacion_id):
    """GH rechaza una postulación exigiendo obligatoriamente un motivo del catálogo."""
    postulacion = get_object_or_404(Postulacion, id=postulacion_id)
    motivo_id = request.POST.get('motivo_rechazo_id')
    observaciones = request.POST.get('observaciones', '').strip()

    if not motivo_id:
        return JsonResponse({'success': False, 'error': 'Debe seleccionar un motivo oficial de rechazo.'})

    motivo = get_object_or_404(MotivoRechazo, id=motivo_id)
    estado_anterior = postulacion.estado

    postulacion.estado = 'RECHAZADA'
    postulacion.motivo_rechazo = motivo
    postulacion.observacion = observaciones
    postulacion.grupo = None
    postulacion.aprobado_por_gh = request.user
    postulacion.fecha_aprobacion_gh = timezone.now()
    postulacion.actualizado_por = request.user.id
    postulacion.save()

    HistorialEstadoPostulacion.objects.create(
        postulacion=postulacion,
        estado_anterior=estado_anterior,
        estado_nuevo='RECHAZADA',
        cambiado_por=request.user.id,
        motivo=f"Rechazado: {motivo.descripcion} - {observaciones}"
    )

    return JsonResponse({'success': True, 'mensaje': 'Postulación rechazada con su respectiva trazabilidad.'})


@login_required
@permiso_requerido('aprobar_gh')
@require_POST
@transaction.atomic
def inscribir_trabajador_gh(request, oferta_id):
    """Inscripción directa por parte de Gestión Humana (excepción)."""
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    trabajador_id = request.POST.get('trabajador_id')
    observacion = request.POST.get('observacion', '').strip()

    if not trabajador_id or not observacion:
        return JsonResponse({'success': False, 'error': 'Debe seleccionar un trabajador y proporcionar una justificación.'})

    trabajador = get_object_or_404(Trabajador, id=trabajador_id, esta_activo=True)

    existente = Postulacion.objects.filter(oferta=oferta, trabajador=trabajador).first()
    if existente and existente.estado not in ['CANCELADA', 'RECHAZADA', 'SUSTITUIDO']:
        return JsonResponse({'success': False, 'error': 'El trabajador ya posee una postulación activa para esta oferta.'})

    if existente:
        existente.estado = 'APROBADA'
        existente.origen_postulacion = 'GESTION_HUMANA'
        existente.observacion = f"Inscripción directa por GH: {observacion}"
        existente.aprobado_por_gh = request.user
        existente.fecha_aprobacion_gh = timezone.now()
        existente.actualizado_por = request.user.id
        existente.save()
        postulacion = existente
    else:
        postulacion = Postulacion.objects.create(
            trabajador=trabajador,
            oferta=oferta,
            estado='APROBADA',
            origen_postulacion='GESTION_HUMANA',
            observacion=f"Inscripción directa por GH: {observacion}",
            aprobado_por_gh=request.user,
            fecha_aprobacion_gh=timezone.now(),
            creado_por=request.user.id,
            actualizado_por=request.user.id,
        )

    HistorialEstadoPostulacion.objects.create(
        postulacion=postulacion,
        estado_anterior=None,
        estado_nuevo='APROBADA',
        cambiado_por=request.user.id,
        motivo=f"Inscrito directamente por GH: {observacion}"
    )

    return JsonResponse({'success': True, 'mensaje': 'Trabajador inscrito y aprobado directamente con éxito.'})


@login_required
@permiso_requerido('aprobar_gh')
@require_POST
@transaction.atomic
def sustituir_participante_gh(request, postulacion_id):
    """Sustituye a un trabajador aprobado por otro con trazabilidad en cadena."""
    postulacion_saliente = get_object_or_404(
        Postulacion.objects.select_related('trabajador__persona', 'oferta', 'grupo'),
        id=postulacion_id
    )
    nuevo_trabajador_id = request.POST.get('nuevo_trabajador_id')
    motivo = request.POST.get('observacion', '').strip() or request.POST.get('motivo', '').strip() or 'Sustitución autorizada por GH.'

    if not nuevo_trabajador_id:
        return JsonResponse({'success': False, 'error': 'Debe seleccionar al trabajador sustituto.'})

    nuevo_trabajador = get_object_or_404(Trabajador.objects.select_related('persona'), id=nuevo_trabajador_id, esta_activo=True)
    oferta = postulacion_saliente.oferta
    grupo_asignado = postulacion_saliente.grupo
    estado_heredado = 'CONFIRMADO' if grupo_asignado else 'APROBADA'

    nombre_entrante = f"{nuevo_trabajador.persona.primer_nombre} {nuevo_trabajador.persona.primer_apellido} (V-{nuevo_trabajador.persona.cedula})"
    nombre_saliente = f"{postulacion_saliente.trabajador.persona.primer_nombre} {postulacion_saliente.trabajador.persona.primer_apellido} (V-{postulacion_saliente.trabajador.persona.cedula})"

    estado_anterior = postulacion_saliente.estado
    postulacion_saliente.estado = 'SUSTITUIDO'
    postulacion_saliente.grupo = None
    postulacion_saliente.observacion = f"Cedió su cupo a {nombre_entrante}. Motivo: {motivo}"
    postulacion_saliente.actualizado_por = request.user.id
    postulacion_saliente.save()

    HistorialEstadoPostulacion.objects.create(
        postulacion=postulacion_saliente,
        estado_anterior=estado_anterior,
        estado_nuevo='SUSTITUIDO',
        cambiado_por=request.user.id,
        motivo=motivo
    )

    nota_entrante = f"Ingresó en sustitución de {nombre_saliente}. Motivo: {motivo}"

    post_entrante = Postulacion.objects.filter(oferta=oferta, trabajador=nuevo_trabajador).first()
    if post_entrante:
        post_entrante.estado = estado_heredado
        post_entrante.grupo = grupo_asignado
        post_entrante.origen_postulacion = 'GESTION_HUMANA'
        post_entrante.sustituye_a = postulacion_saliente
        post_entrante.observacion = nota_entrante
        post_entrante.aprobado_por_gh = request.user
        post_entrante.fecha_aprobacion_gh = timezone.now()
        post_entrante.actualizado_por = request.user.id
        post_entrante.save()
        nueva_post = post_entrante
    else:
        nueva_post = Postulacion.objects.create(
            trabajador=nuevo_trabajador,
            oferta=oferta,
            grupo=grupo_asignado,
            estado=estado_heredado,
            origen_postulacion='GESTION_HUMANA',
            sustituye_a=postulacion_saliente,
            observacion=nota_entrante,
            aprobado_por_gh=request.user,
            fecha_aprobacion_gh=timezone.now(),
            creado_por=request.user.id,
            actualizado_por=request.user.id,
        )

    HistorialEstadoPostulacion.objects.create(
        postulacion=nueva_post,
        estado_anterior=None,
        estado_nuevo=estado_heredado,
        cambiado_por=request.user.id,
        motivo=nota_entrante
    )

    return JsonResponse({
        'success': True,
        'mensaje': f'Sustitución completada: {nombre_entrante} tomó el cupo de {nombre_saliente}.'
    })


# =============================================================================
# 4. PESTAÑA 2 DEL WORKSPACE GH: GRUPOS Y LISTA DE ASISTENCIA EN PDF (+5 FILAS)
# =============================================================================

@login_required
@permiso_requerido('ver_ofertas_formacion')
def listar_grupos(request, oferta_id):
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    grupos = GrupoOferta.objects.filter(oferta=oferta, esta_activo=True).prefetch_related(
        'participantes__trabajador__persona',
        'participantes__trabajador__unidad_org'
    ).order_by('fecha_inicio', 'id')

    postulaciones_sin_grupo = Postulacion.objects.filter(
        oferta=oferta,
        estado__in=['APROBADA', 'APROBADO_GH'],
        grupo__isnull=True
    ).select_related('trabajador__persona', 'trabajador__unidad_org', 'trabajador__cargo_estructural')

    return render(request, 'formacion/gestion_humana/listar_grupos.html', {
        'oferta': oferta,
        'grupos': grupos,
        'postulaciones_sin_grupo': postulaciones_sin_grupo,
    })


@login_required
@permiso_requerido('crear_oferta')
@require_POST
def crear_grupo(request, oferta_id):
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    try:
        trabajadores_ids = request.POST.getlist('trabajadores_ids') or request.POST.getlist('trabajadores_ids[]')
        cupo_grupo = int(request.POST.get('cupo_maximo', 20))

        if len(trabajadores_ids) > cupo_grupo:
            return JsonResponse({'success': False, 'error': f'Seleccionaste {len(trabajadores_ids)} personas, pero el cupo máximo es {cupo_grupo}.'})

        with transaction.atomic():
            grupo = GrupoOferta.objects.create(
                oferta=oferta,
                nombre_grupo=request.POST.get('nombre_grupo', '').strip().upper(),
                fecha_inicio=request.POST.get('fecha_inicio') or None,
                fecha_fin=request.POST.get('fecha_fin') or None,
                horario=request.POST.get('horario', '').strip().upper() or None,
                lugar=request.POST.get('lugar', '').strip().upper() or None,
                instructor=request.POST.get('instructor', '').strip().upper() or None,
                cupo_maximo=cupo_grupo,
                creado_por=request.user.id,
                actualizado_por=request.user.id,
            )

            if trabajadores_ids:
                Postulacion.objects.filter(
                    oferta=oferta,
                    trabajador_id__in=trabajadores_ids,
                    estado__in=['APROBADA', 'APROBADO_GH'],
                    grupo__isnull=True
                ).update(
                    grupo=grupo,
                    estado='CONFIRMADO',
                    actualizado_por=request.user.id
                )

        return JsonResponse({
            'success': True,
            'mensaje': f'Grupo "{grupo.nombre_grupo}" creado con {len(trabajadores_ids)} participantes.'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permiso_requerido('editar_oferta')
def editar_grupo(request, grupo_id):
    grupo = get_object_or_404(GrupoOferta.objects.select_related('oferta'), id=grupo_id)
    oferta = grupo.oferta

    if request.method == 'POST':
        try:
            grupo.nombre_grupo = request.POST.get('nombre_grupo', grupo.nombre_grupo).strip().upper()
            grupo.fecha_inicio = request.POST.get('fecha_inicio') or None
            grupo.fecha_fin = request.POST.get('fecha_fin') or None
            grupo.horario = request.POST.get('horario', '').strip().upper() or None
            grupo.lugar = request.POST.get('lugar', '').strip().upper() or None
            grupo.instructor = request.POST.get('instructor', '').strip().upper() or None
            grupo.cupo_maximo = int(request.POST.get('cupo_maximo', grupo.cupo_maximo))
            grupo.actualizado_por = request.user.id
            grupo.save()
            return JsonResponse({'success': True, 'mensaje': 'Grupo actualizado correctamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    participantes = Postulacion.objects.filter(grupo=grupo).select_related('trabajador__persona', 'trabajador__unidad_org')
    disponibles = Postulacion.objects.filter(
        oferta=oferta, estado__in=['APROBADA', 'APROBADO_GH'], grupo__isnull=True
    ).select_related('trabajador__persona', 'trabajador__unidad_org')

    return render(request, 'planificacion/editar_grupo.html', {
        'grupo': grupo,
        'participantes': participantes,
        'disponibles': disponibles,
    })


@login_required
@permiso_requerido('ver_ofertas_formacion')
def descargar_lista_asistencia_pdf(request, grupo_id):
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    grupo = get_object_or_404(GrupoOferta.objects.select_related('oferta__tipo_formacion', 'oferta__modalidad'), id=grupo_id)
    oferta = grupo.oferta
    participantes = Postulacion.objects.filter(
        grupo=grupo
    ).exclude(estado__in=['CANCELADA', 'SUSTITUIDO', 'RECHAZADA']).select_related(
        'trabajador__persona', 'trabajador__unidad_org'
    ).order_by('trabajador__persona__primer_apellido', 'trabajador__persona__primer_nombre')

    institucion_info = IdentidadInstitucional.objects.first()
    nombre_ente = institucion_info.nombre_oficial if institucion_info else "ALMACENADORA CARACAS, C.A."

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleCustom', parent=styles['Heading1'], fontSize=13, textColor=colors.HexColor('#1E3A8A'), alignment=1, spaceAfter=4)
    sub_style = ParagraphStyle('SubCustom', parent=styles['Normal'], fontSize=9, alignment=1, textColor=colors.HexColor('#475569'), spaceAfter=12)
    cell_style = ParagraphStyle('CellCustom', parent=styles['Normal'], fontSize=8, leading=10)

    elements.append(Paragraph(f"<b>{nombre_ente} - OFICINA DE GESTIÓN HUMANA</b>", sub_style))
    elements.append(Paragraph(f"CONTROL DE ASISTENCIA: {oferta.nombre}", title_style))

    f_ini = grupo.fecha_inicio.strftime('%d/%m/%Y') if grupo.fecha_inicio else 'Por definir'
    f_fin = grupo.fecha_fin.strftime('%d/%m/%Y') if grupo.fecha_fin else 'Por definir'
    meta_info = (
        f"<b>Grupo:</b> {grupo.nombre_grupo} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Institución:</b> {oferta.institucion} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Facilitador:</b> {grupo.instructor or 'Por definir'}<br/>"
        f"<b>Fechas:</b> {f_ini} al {f_fin} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Horario:</b> {grupo.horario or 'Por definir'} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Lugar:</b> {grupo.lugar or 'Sede Corporativa'} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Duración:</b> {oferta.horas_academicas} hrs"
    )
    elements.append(Paragraph(meta_info, sub_style))
    elements.append(Spacer(1, 6))

    data = [['N°', 'CÉDULA', 'NOMBRES Y APELLIDOS', 'UNIDAD ORGANIZATIVA', 'CORREO ELECTRÓNICO', 'FIRMA DEL PARTICIPANTE']]

    contador = 1
    for p in participantes:
        per = p.trabajador.persona
        nombre_completo = f"{per.primer_apellido} {per.segundo_apellido or ''}, {per.primer_nombre} {per.segundo_nombre or ''}".strip()
        unidad_nombre = p.trabajador.unidad_org.nombre_unidad if p.trabajador.unidad_org else "—"

        correo = "—"
        rel_correo = per.personacontactopersonal_set.filter(esta_activo=True, contacto_personal__tipo_contacto_id=3).select_related('contacto_personal').first()
        if rel_correo and rel_correo.contacto_personal:
            correo = rel_correo.contacto_personal.valor_contacto

        data.append([
            str(contador),
            f"V-{per.cedula}",
            Paragraph(nombre_completo, cell_style),
            Paragraph(unidad_nombre, cell_style),
            Paragraph(correo, cell_style),
            ""
        ])
        contador += 1

    for _ in range(5):
        data.append([str(contador), "", "", "", "", ""])
        contador += 1

    col_widths = [30, 75, 195, 185, 145, 100]
    table = Table(data, colWidths=col_widths, repeatRows=1, rowHeights=[24] + [24] * (len(data) - 1))
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("___________________________________________<br/><b>Firma del Facilitador / Responsable de Gestión Humana</b>", sub_style))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    filename = f"Lista_Asistencia_{grupo.nombre_grupo.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    response.write(pdf)
    return response


# =============================================================================
# 5. PESTAÑA 3 Y 4 DEL WORKSPACE GH: ASISTENCIA Y CERTIFICADOS
# =============================================================================

@login_required
@permiso_requerido('ver_ofertas_formacion')
def workspace_asistencia(request, oferta_id):
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    grupos = GrupoOferta.objects.filter(oferta=oferta, esta_activo=True).order_by('id')

    grupo_seleccionado_id = request.GET.get('grupo_id')
    if grupo_seleccionado_id:
        grupo_actual = grupos.filter(id=grupo_seleccionado_id).first()
    else:
        grupo_actual = grupos.first()

    participantes = []
    trabajadores_no_inscritos = []

    if grupo_actual:
        postulaciones_grupo = Postulacion.objects.filter(
            grupo=grupo_actual
        ).exclude(estado__in=['CANCELADA', 'SUSTITUIDO', 'RECHAZADA']).select_related(
            'trabajador__persona', 'trabajador__unidad_org', 'trabajador__cargo_estructural'
        ).prefetch_related('asistencias').order_by('trabajador__persona__primer_apellido')

        for p in postulaciones_grupo:
            p.asistencia_obj = p.asistencias.first()
            participantes.append(p)

        ids_en_oferta = Postulacion.objects.filter(
            oferta=oferta
        ).exclude(estado__in=['CANCELADA', 'SUSTITUIDO']).values_list('trabajador_id', flat=True)

        trabajadores_no_inscritos = Trabajador.objects.filter(
            esta_activo=True
        ).exclude(id__in=ids_en_oferta).select_related('persona', 'unidad_org').order_by('persona__primer_nombre')

    return render(request, 'formacion/gestion_humana/workspace_asistencia.html', {
        'oferta': oferta,
        'grupos': grupos,
        'grupo_actual': grupo_actual,
        'participantes': participantes,
        'trabajadores_no_inscritos': trabajadores_no_inscritos,
    })


@login_required
@permiso_requerido('editar_oferta')
@require_POST
@transaction.atomic
def guardar_asistencia_grupo(request, grupo_id):
    grupo = get_object_or_404(GrupoOferta.objects.select_related('oferta'), id=grupo_id)
    postulaciones_grupo = Postulacion.objects.filter(grupo=grupo).exclude(estado__in=['CANCELADA', 'SUSTITUIDO', 'RECHAZADA'])

    try:
        archivo_acta = request.FILES.get('archivo_acta_asistencia')
        if archivo_acta:
            carpeta_rel = f"formacion/actas_asistencia/oferta_{grupo.oferta.id}"
            ruta_completa_dir = os.path.join(settings.MEDIA_ROOT, carpeta_rel)
            os.makedirs(ruta_completa_dir, exist_ok=True)
            fs = FileSystemStorage(location=ruta_completa_dir)
            ext = os.path.splitext(archivo_acta.name)[1]
            nombre_limpio = f"acta_grupo_{grupo.id}_{int(timezone.now().timestamp())}{ext}"
            fs.save(nombre_limpio, archivo_acta)
            grupo.archivo_acta_asistencia = f"{carpeta_rel}/{nombre_limpio}"
            grupo.save()

        asistentes_marcados = request.POST.getlist('asistio_ids')
        for post in postulaciones_grupo:
            marco_asistio = str(post.id) in asistentes_marcados
            nota = request.POST.get(f'nota_{post.id}', '').strip()
            if not marco_asistio and not nota:
                nota = 'Inasistente según lista de control física.'

            asist_obj = Asistencia.objects.filter(postulacion=post).first()
            if asist_obj:
                asist_obj.asistio = marco_asistio
                asist_obj.observacion_asistencia = nota
                if grupo.archivo_acta_asistencia:
                    asist_obj.archivo_lista = grupo.archivo_acta_asistencia
                asist_obj.actualizado_por = request.user.id
                asist_obj.save()
            else:
                Asistencia.objects.create(
                    postulacion=post,
                    asistio=marco_asistio,
                    observacion_asistencia=nota,
                    archivo_lista=grupo.archivo_acta_asistencia,
                    creado_por=request.user.id,
                    actualizado_por=request.user.id
                )

        return JsonResponse({'success': True, 'mensaje': 'Control de asistencia y soporte guardados correctamente.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permiso_requerido('editar_oferta')
@require_POST
@transaction.atomic
def agregar_asistente_sitio(request, grupo_id):
    grupo = get_object_or_404(GrupoOferta.objects.select_related('oferta'), id=grupo_id)
    trabajador_id = request.POST.get('trabajador_id')
    observacion = request.POST.get('observacion', '').strip() or 'Incorporado en sitio (Firmó en lista física de asistencia).'

    if not trabajador_id:
        return JsonResponse({'success': False, 'error': 'Seleccione al trabajador que asistió.'})

    trabajador = get_object_or_404(Trabajador.objects.select_related('persona'), id=trabajador_id, esta_activo=True)

    post, created = Postulacion.objects.update_or_create(
        oferta=grupo.oferta,
        trabajador=trabajador,
        defaults={
            'grupo': grupo,
            'estado': 'CONFIRMADO',
            'origen_postulacion': 'ASISTENCIA_SITIO',
            'observacion': observacion,
            'aprobado_por_gh': request.user,
            'fecha_aprobacion_gh': timezone.now(),
            'creado_por': request.user.id,
            'actualizado_por': request.user.id,
        }
    )

    Asistencia.objects.update_or_create(
        postulacion=post,
        defaults={
            'asistio': True,
            'observacion_asistencia': observacion,
            'archivo_lista': grupo.archivo_acta_asistencia,
            'creado_por': request.user.id,
            'actualizado_por': request.user.id,
        }
    )

    return JsonResponse({
        'success': True,
        'mensaje': f'{trabajador.persona.primer_nombre} {trabajador.persona.primer_apellido} fue registrado como Asistente en Sitio y ya tiene habilitada la carga de su certificado.'
    })


@login_required
@require_POST
@transaction.atomic
def cargar_certificado(request, postulacion_id):
    postulacion = get_object_or_404(
        Postulacion.objects.select_related('trabajador__persona', 'oferta', 'grupo'),
        id=postulacion_id
    )

    rol_nombre = request.user.rol.nombre_rol.upper() if getattr(request.user, 'rol', None) else ''
    es_gh = any(p in rol_nombre for p in ['GESTION', 'ADMINISTRADOR', 'SUPERUSUARIO', 'HUMANA']) or _es_admin_prueba(request.user)
    es_dueno = (postulacion.trabajador.persona.cedula == request.user.nombre_usuario)

    if not (es_gh or es_dueno):
        return JsonResponse({'success': False, 'error': 'No tienes permiso para cargar este certificado.'})

    asistencia = Asistencia.objects.filter(postulacion=postulacion, asistio=True).first()
    if not asistencia:
        return JsonResponse({
            'success': False,
            'error': 'Solo se puede cargar certificado a los participantes marcados como ASISTIÓ.'
        })

    archivo = request.FILES.get('archivo_certificado')
    if not archivo:
        return JsonResponse({'success': False, 'error': 'Debe seleccionar un archivo PDF o imagen.'})

    cedula = postulacion.trabajador.persona.cedula
    carpeta_rel = f"recaudos/trabajador_{cedula}/certificados"
    ruta_completa_dir = os.path.join(settings.MEDIA_ROOT, carpeta_rel)
    os.makedirs(ruta_completa_dir, exist_ok=True)

    fs = FileSystemStorage(location=ruta_completa_dir)
    ext = os.path.splitext(archivo.name)[1]
    nombre_archivo = f"cert_oferta_{postulacion.oferta.id}_{int(timezone.now().timestamp())}{ext}"
    fs.save(nombre_archivo, archivo)
    ruta_relativa = f"{carpeta_rel}/{nombre_archivo}"

    asistencia.ruta_certificado = ruta_relativa
    asistencia.fecha_carga_certificado = timezone.now()
    asistencia.certificado_cargado_por = request.user.id
    asistencia.actualizado_por = request.user.id
    asistencia.save()

    recaudo_cert = Recaudo.objects.create(
        trabajador=postulacion.trabajador,
        tipo_recaudo_id=6,
        ruta_archivo=ruta_relativa,
        observaciones=f"Certificado institucional SACAT: {postulacion.oferta.nombre}",
        esta_activo=True,
        creado_por=request.user.id,
        actualizado_por=request.user.id,
    )

    fecha_culm = (
        postulacion.grupo.fecha_fin
        if (postulacion.grupo and postulacion.grupo.fecha_fin)
        else postulacion.oferta.fecha_cierre_postulacion
    )

    FormacionAdicional.objects.update_or_create(
        persona=postulacion.trabajador.persona,
        nombre_formacion_ad=postulacion.oferta.nombre,
        institucion=postulacion.oferta.institucion,
        defaults={
            'duracion_horas': postulacion.oferta.horas_academicas,
            'fecha_culminacion': fecha_culm,
            'tipo_formacion_id': postulacion.oferta.tipo_formacion_id,
            'modalidad_id': postulacion.oferta.modalidad_id,
            'recaudo': recaudo_cert,
            'esta_activo': True,
            'creado_por': request.user.id,
            'actualizado_por': request.user.id,
        }
    )

    return JsonResponse({
        'success': True,
        'mensaje': 'Certificado cargado exitosamente y sincronizado con la Ficha Curricular del trabajador.'
    })


@login_required
@permiso_requerido('ver_ofertas_formacion')
def workspace_curso_view(request, oferta_id):
    """Renderiza el Workspace centralizado de Gestión Humana manejando las pestañas dinámicamente."""
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    tab = request.GET.get('tab', 'postulaciones')
    
    context = {
        'oferta': oferta,
        'active_tab': tab,  # <-- Aquí estaba la diferencia: pasamos active_tab para que el HTML lo reconozca
        'total_postulados': oferta.postulaciones.exclude(estado='CANCELADA').count(),
        'total_pendientes': oferta.postulaciones.filter(estado='PENDIENTE').count(),
        'total_grupos': oferta.grupos.filter(esta_activo=True).count(),
    }

    # PESTAÑA 1: POSTULACIONES Y APROBACIÓN
    if tab == 'postulaciones' or not tab:
        postulaciones = oferta.postulaciones.select_related(
            'trabajador__persona', 'trabajador__unidad_org', 'trabajador__cargo_estructural',
            'grupo', 'sustituye_a__trabajador__persona'
        ).order_by('-fecha_postulacion')
        
        oficina_id = request.GET.get('oficina')
        estado_filtro = request.GET.get('estado')
        q = request.GET.get('q')
        
        if oficina_id:
            postulaciones = postulaciones.filter(trabajador__unidad_org_id=oficina_id)
        if estado_filtro:
            postulaciones = postulaciones.filter(estado=estado_filtro)
        if q:
            postulaciones = postulaciones.filter(
                Q(trabajador__persona__cedula__icontains=q) |
                Q(trabajador__persona__primer_nombre__icontains=q) |
                Q(trabajador__persona__primer_apellido__icontains=q)
            )

        unidades = UnidadesOrganizativas.objects.filter(esta_activo=True).order_by('nombre_unidad')
        ids_inscritos = oferta.postulaciones.exclude(estado__in=['CANCELADA', 'SUSTITUIDO', 'RECHAZADA']).values_list('trabajador_id', flat=True)
        trabajadores_disponibles = Trabajador.objects.filter(esta_activo=True).exclude(id__in=ids_inscritos).select_related('persona', 'unidad_org').order_by('persona__primer_nombre')
        
        aprobados = oferta.postulaciones.filter(estado__in=['APROBADA', 'APROBADO_GH', 'CONFIRMADO']).count()
        pendientes = oferta.postulaciones.filter(estado='PENDIENTE').count()
        rechazados = oferta.postulaciones.filter(estado__in=['RECHAZADA', 'RECHAZADO_GH']).count()
        cupo_max = oferta.cupo_maximo_oferta or 50

        context.update({
            'postulaciones': postulaciones,
            'unidades': unidades,
            'trabajadores_disponibles': trabajadores_disponibles,
            'motivos_rechazo': MotivoRechazo.objects.filter(esta_activo=True),
            'metricas': {
                'cupo_max': cupo_max,
                'aprobados': aprobados,
                'pendientes': pendientes,
                'rechazados': rechazados,
                'disponibles': max(0, cupo_max - aprobados),
            }
        })

    # PESTAÑA 2: PLANIFICACIÓN DE GRUPOS
    elif tab == 'grupos':
        grupos = oferta.grupos.filter(esta_activo=True).prefetch_related(
            'participantes__trabajador__persona', 'participantes__trabajador__unidad_org'
        ).order_by('fecha_inicio', 'id')
        
        postulaciones_sin_grupo = oferta.postulaciones.filter(
            estado__in=['APROBADA', 'APROBADO_GH'], grupo__isnull=True
        ).select_related('trabajador__persona', 'trabajador__unidad_org', 'trabajador__cargo_estructural')

        context.update({
            'grupos': grupos,
            'postulaciones_sin_grupo': postulaciones_sin_grupo,
        })

    # PESTAÑA 3: CONTROL DE ASISTENCIA
    elif tab == 'asistencia':
        grupos = oferta.grupos.filter(esta_activo=True).order_by('id')
        grupo_seleccionado_id = request.GET.get('grupo_id')
        grupo_seleccionado = grupos.filter(id=grupo_seleccionado_id).first() if grupo_seleccionado_id else grupos.first()
        
        participantes_asistencia = []
        trabajadores_disponibles = []
        if grupo_seleccionado:
            postulaciones_grupo = oferta.postulaciones.filter(
                grupo=grupo_seleccionado
            ).exclude(estado__in=['CANCELADA', 'SUSTITUIDO', 'RECHAZADA']).select_related(
                'trabajador__persona', 'trabajador__unidad_org'
            ).prefetch_related('asistencias').order_by('trabajador__persona__primer_apellido')

            for p in postulaciones_grupo:
                asist_obj = p.asistencias.first()
                participantes_asistencia.append({
                    'postulacion': p,
                    'asistio': asist_obj.asistio if asist_obj else False,
                    'observacion_asistencia': asist_obj.observacion_asistencia if asist_obj else ''
                })

            ids_en_oferta = oferta.postulaciones.exclude(estado__in=['CANCELADA', 'SUSTITUIDO']).values_list('trabajador_id', flat=True)
            trabajadores_disponibles = Trabajador.objects.filter(esta_activo=True).exclude(id__in=ids_en_oferta).select_related('persona', 'unidad_org').order_by('persona__primer_nombre')

        context.update({
            'grupos': grupos,
            'grupo_seleccionado': grupo_seleccionado,
            'participantes_asistencia': participantes_asistencia,
            'trabajadores_disponibles': trabajadores_disponibles,
        })

    # PESTAÑA 4: CERTIFICADOS
    elif tab == 'certificados':
        participantes_certificables = oferta.postulaciones.filter(
            estado__in=['APROBADA', 'APROBADO_GH', 'CONFIRMADO']
        ).select_related('trabajador__persona', 'trabajador__unidad_org', 'grupo').prefetch_related('asistencias', 'certificados').order_by('trabajador__persona__primer_apellido')
        
        context.update({
            'participantes_certificables': participantes_certificables,
        })

    return render(request, 'formacion/gestion_humana/workspace_curso.html', context)