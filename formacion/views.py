from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.conf import settings

# Decorador personalizado de permisos
from seguridad.decorators import permiso_requerido

# Modelos de formación
from .models import OfertaFormacion, Postulacion, GrupoOferta

# Modelos de catálogo
from configuracion.models import TipoFormacion, Modalidad, UnidadesOrganizativas

# Modelo de trabajador
from trabajadores.models import Trabajador


# =============================================================================
# SUBMÓDULO: OFERTAS DE FORMACIÓN (GESTIÓN HUMANA)
# =============================================================================

@login_required
@permiso_requerido('ver_ofertas_formacion')  # 🆕
def listar_ofertas(request):
    """Listar todas las ofertas de formación."""
    ofertas = OfertaFormacion.objects.select_related('tipo_formacion', 'modalidad').all().order_by('-fecha_publicacion')
    return render(request, 'ofertas/listar_ofertas.html', {'ofertas': ofertas})


@login_required
@permiso_requerido('crear_oferta')  # 🆕
def crear_oferta(request):
    """Crear una nueva oferta de formación."""
    if request.method == 'POST':
        try:
            OfertaFormacion.objects.create(
                tipo_formacion_id=request.POST.get('tipo_formacion_id'),
                modalidad_id=request.POST.get('modalidad_id'),
                institucion=request.POST.get('institucion', '').strip().upper(),
                nombre=request.POST.get('nombre', '').strip().upper(),
                descripcion=request.POST.get('descripcion', '').strip(),
                horas_academicas=request.POST.get('horas_academicas'),
                fecha_publicacion=request.POST.get('fecha_publicacion'),
                fecha_cierre_postulacion=request.POST.get('fecha_cierre_postulacion'),
                estado_oferta='ABIERTA',
                creado_por=request.user.id,
                actualizado_por=request.user.id,
            )
            return JsonResponse({'success': True, 'mensaje': 'Oferta creada exitosamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    tipos = TipoFormacion.objects.filter(esta_activo=True)
    modalidades = Modalidad.objects.filter(esta_activo=True)
    return render(request, 'ofertas/crear_oferta.html', {'tipos': tipos, 'modalidades': modalidades})


@login_required
@permiso_requerido('editar_oferta')  # 🆕
def editar_oferta(request, oferta_id):
    """Editar una oferta de formación existente."""
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)

    if request.method == 'POST':
        try:
            oferta.tipo_formacion_id = request.POST.get('tipo_formacion_id')
            oferta.modalidad_id = request.POST.get('modalidad_id')
            oferta.institucion = request.POST.get('institucion', '').strip().upper()
            oferta.nombre = request.POST.get('nombre', '').strip().upper()
            oferta.descripcion = request.POST.get('descripcion', '').strip()
            oferta.horas_academicas = request.POST.get('horas_academicas')
            oferta.fecha_publicacion = request.POST.get('fecha_publicacion')
            oferta.fecha_cierre_postulacion = request.POST.get('fecha_cierre_postulacion')
            oferta.actualizado_por = request.user.id
            oferta.save()
            return JsonResponse({'success': True, 'mensaje': 'Oferta actualizada correctamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    tipos = TipoFormacion.objects.filter(esta_activo=True)
    modalidades = Modalidad.objects.filter(esta_activo=True)
    return render(request, 'ofertas/editar_oferta.html', {'oferta': oferta, 'tipos': tipos, 'modalidades': modalidades})


@login_required
@permiso_requerido('inhabilitar_oferta')  # 🆕
@require_POST
def toggle_oferta(request, oferta_id):
    """Activar o inhabilitar una oferta de formación."""
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    oferta.esta_activo = not oferta.esta_activo
    oferta.actualizado_por = request.user.id
    oferta.save()
    estado = "habilitada" if oferta.esta_activo else "inhabilitada"
    return JsonResponse({'success': True, 'mensaje': f'Oferta {estado}.'})


# =============================================================================
# SUBMÓDULO: POSTULACIONES (TRABAJADOR)
# =============================================================================

@login_required
@permiso_requerido('ver_ofertas_activas')  # 🆕
def listar_ofertas_activas(request):
    """
    Vista del trabajador: muestra las ofertas en estado ABIERTA
    en las que aún no se ha postulado.
    """
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)

    ofertas = OfertaFormacion.objects.filter(
        estado_oferta='ABIERTA',
        esta_activo=True
    ).exclude(
        postulaciones__trabajador=trabajador
    ).select_related('tipo_formacion', 'modalidad').order_by('-fecha_publicacion')

    return render(request, 'postulaciones/listar_ofertas_activas.html', {'ofertas': ofertas})


@login_required
@permiso_requerido('postular_oferta')  # 🆕
@require_POST
def postular_oferta(request, oferta_id):
    """
    El trabajador se postula a una oferta.
    Crea un registro en la tabla postulaciones con estado PENDIENTE.
    """
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id, estado_oferta='ABIERTA', esta_activo=True)

    if Postulacion.objects.filter(trabajador=trabajador, oferta=oferta).exists():
        return JsonResponse({'success': False, 'error': 'Ya te has postulado a esta oferta.'})

    Postulacion.objects.create(
        trabajador=trabajador,
        oferta=oferta,
        estado='PENDIENTE',
        creado_por=request.user.id,
    )
    return JsonResponse({'success': True, 'mensaje': 'Te has postulado exitosamente.'})


@login_required
@permiso_requerido('ver_mis_postulaciones')  # 🆕
def listar_postulaciones(request):
    """
    El trabajador ve el historial de sus postulaciones.
    """
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    postulaciones = Postulacion.objects.filter(
        trabajador=trabajador
    ).select_related('oferta__tipo_formacion', 'oferta__modalidad', 'grupo').order_by('-fecha_postulacion')

    return render(request, 'postulaciones/listar_postulaciones.html', {'postulaciones': postulaciones})


# =============================================================================
# SUBMÓDULO: APROBACIÓN DE POSTULACIONES (JEFE + GH)
# =============================================================================

def _obtener_unidades_hijas(unidad_base):
    """
    Retorna una lista con los IDs de la unidad base y todas sus unidades hijas (recursivo).
    Ejemplo: OFICINA DE GESTIÓN HUMANA (ID 4) retorna [4, 22, 23, 24]
    """
    ids = [unidad_base.id]
    hijas = UnidadesOrganizativas.objects.filter(unidad_sup=unidad_base, esta_activo=True)
    
    for hija in hijas:
        ids.extend(_obtener_unidades_hijas(hija))
    
    return ids

@login_required
@permiso_requerido('ver_bandeja_aprobacion')
def bandeja_aprobacion(request):
    """
    Muestra las postulaciones según el perfil del usuario:
    - Jefe (cargo en CARGOS_JEFE): postulaciones PENDIENTES de su unidad Y unidades hijas.
    - GH (rol Gestión Humana/Administrador): postulaciones APROBADAS por jefes.
    """
    user = request.user
    rol_nombre = user.rol.nombre_rol.upper() if user.rol else ''

    trabajador_user = Trabajador.objects.filter(
        persona__cedula=user.nombre_usuario
    ).select_related('unidad_org', 'cargo_estructural').first()

    postulaciones_jefe = []
    postulaciones_gh = []
    ofertas_con_cupos = []
    es_jefe = False
    es_gh = any(p in rol_nombre for p in ['GESTION', 'ADMINISTRADOR', 'SUPERUSUARIO', 'HUMANA'])

    # Detección por cargo estructural usando settings.CARGOS_JEFE
    if trabajador_user and trabajador_user.cargo_estructural and trabajador_user.unidad_org:
        cargo_usuario = trabajador_user.cargo_estructural.nombre_cargo_estruct.upper()
        es_jefe = any(cargo_jefe in cargo_usuario for cargo_jefe in settings.CARGOS_JEFE)
        
        if es_jefe:
            # Obtener todas las unidades bajo su mando (su unidad + hijas)
            unidades_a_cargo = _obtener_unidades_hijas(trabajador_user.unidad_org)
            
            postulaciones_jefe = Postulacion.objects.filter(
                trabajador__unidad_org__in=unidades_a_cargo,
                trabajador__esta_activo=True,
                estado='PENDIENTE'
            ).select_related(
                'trabajador__persona', 
                'trabajador__cargo_estructural',
                'trabajador__unidad_org',
                'oferta'
            ).order_by('-fecha_postulacion')

    # GH: Postulaciones aprobadas por jefes + cálculo de cupos
    if es_gh:
        # Obtener todas las ofertas con postulaciones para calcular cupos
        ofertas_ids = Postulacion.objects.filter(
            estado__in=['PENDIENTE', 'APROBADO_JEFE', 'APROBADO_GH', 'CONFIRMADO']
        ).values_list('oferta_id', flat=True).distinct()
        
        ofertas = OfertaFormacion.objects.filter(id__in=ofertas_ids, esta_activo=True)
        
        for oferta in ofertas:
            aprobadas = Postulacion.objects.filter(
                oferta=oferta, estado__in=['APROBADO_GH', 'CONFIRMADO']
            ).count()
            por_aprobar = Postulacion.objects.filter(
                oferta=oferta, estado__in=['PENDIENTE', 'APROBADO_JEFE']
            ).count()
            cupo_total = oferta.cupo_maximo_oferta or 50
            disponibles = cupo_total - aprobadas - por_aprobar
            
            ofertas_con_cupos.append({
                'oferta': oferta,
                'aprobadas': aprobadas,
                'por_aprobar': por_aprobar,
                'disponibles': max(0, disponibles),
                'cupo_total': cupo_total,
            })
        
        postulaciones_gh = Postulacion.objects.filter(
            estado='APROBADO_JEFE'
        ).select_related(
            'trabajador__persona', 
            'trabajador__unidad_org', 
            'oferta'
        ).order_by('-fecha_postulacion')

    return render(request, 'aprobacion/bandeja_aprobacion.html', {
        'postulaciones_jefe': postulaciones_jefe,
        'postulaciones_gh': postulaciones_gh,
        'ofertas_con_cupos': ofertas_con_cupos,
        'es_jefe': es_jefe,
        'es_gh': es_gh,
    })

# =============================================================================
# DETALLE DE POSTULACIONES PARA MODAL (AJAX)
# =============================================================================

@login_required
@permiso_requerido('ver_bandeja_aprobacion')
def detalle_jefe(request, oferta_id):
    """Retorna el detalle de postulaciones pendientes de una oferta (vista Jefe)."""
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    
    trabajador_user = Trabajador.objects.filter(
        persona__cedula=request.user.nombre_usuario
    ).select_related('unidad_org').first()
    
    if trabajador_user and trabajador_user.unidad_org:
        unidades_a_cargo = _obtener_unidades_hijas(trabajador_user.unidad_org)
        postulaciones = Postulacion.objects.filter(
            oferta=oferta,
            trabajador__unidad_org__in=unidades_a_cargo,
            estado='PENDIENTE'
        ).select_related('trabajador__persona', 'trabajador__cargo_estructural')
    else:
        postulaciones = []
    
    return render(request, 'aprobacion/detalle_jefe.html', {
        'oferta': oferta,
        'postulaciones': postulaciones,
    })


@login_required
@permiso_requerido('ver_bandeja_aprobacion')
def detalle_gh(request, oferta_id):
    """Retorna el detalle de postulaciones aprobadas por jefe (vista GH)."""
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    
    postulaciones = Postulacion.objects.filter(
        oferta=oferta,
        estado='APROBADO_JEFE'
    ).select_related('trabajador__persona', 'trabajador__unidad_org')
    
    return render(request, 'aprobacion/detalle_gh.html', {
        'oferta': oferta,
        'postulaciones': postulaciones,
    })
# --- Acciones del Jefe ---

@login_required
@permiso_requerido('aprobar_jefe')  # 🆕
@require_POST
def aprobar_jefe(request, postulacion_id):
    """El jefe aprueba una postulación de su unidad."""
    postulacion = get_object_or_404(Postulacion, id=postulacion_id, estado='PENDIENTE')
    postulacion.estado = 'APROBADO_JEFE'
    postulacion.aprobado_por_jefe = request.user
    postulacion.fecha_aprobacion_jefe = timezone.now()
    postulacion.save()
    return JsonResponse({'success': True})


@login_required
@permiso_requerido('rechazar_jefe')  # 🆕
@require_POST
def rechazar_jefe(request, postulacion_id):
    """El jefe rechaza una postulación de su unidad."""
    postulacion = get_object_or_404(Postulacion, id=postulacion_id, estado='PENDIENTE')
    postulacion.estado = 'RECHAZADO_JEFE'
    postulacion.aprobado_por_jefe = request.user
    postulacion.fecha_aprobacion_jefe = timezone.now()
    postulacion.save()
    return JsonResponse({'success': True})


# --- Acciones de Gestión Humana ---

@login_required
@permiso_requerido('aprobar_gh')  # 🆕
@require_POST
def aprobar_gh(request, postulacion_id):
    """GH aprueba una postulación ya aprobada por el jefe."""
    postulacion = get_object_or_404(Postulacion, id=postulacion_id, estado='APROBADO_JEFE')
    postulacion.estado = 'APROBADO_GH'
    postulacion.aprobado_por_gh = request.user
    postulacion.fecha_aprobacion_gh = timezone.now()
    postulacion.save()
    return JsonResponse({'success': True})


@login_required
@permiso_requerido('rechazar_gh')  # 🆕
@require_POST
def rechazar_gh(request, postulacion_id):
    """GH rechaza una postulación ya aprobada por el jefe."""
    postulacion = get_object_or_404(Postulacion, id=postulacion_id, estado='APROBADO_JEFE')
    postulacion.estado = 'RECHAZADO_GH'
    postulacion.aprobado_por_gh = request.user
    postulacion.fecha_aprobacion_gh = timezone.now()
    postulacion.save()
    return JsonResponse({'success': True})


# =============================================================================
# SUBMÓDULO: PLANIFICACIÓN (GESTIÓN HUMANA)
# =============================================================================

@login_required
@permiso_requerido('ver_ofertas_formacion')
def listar_grupos(request, oferta_id):
    """Lista los grupos creados para una oferta específica."""
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    grupos = GrupoOferta.objects.filter(oferta=oferta, esta_activo=True).order_by('fecha_inicio')
    
    # Postulaciones aprobadas por GH sin grupo asignado
    postulaciones_sin_grupo = Postulacion.objects.filter(
        oferta=oferta,
        estado='APROBADO_GH',
        grupo__isnull=True
    ).select_related('trabajador__persona')
    
    return render(request, 'planificacion/listar_grupos.html', {
        'oferta': oferta,
        'grupos': grupos,
        'postulaciones_sin_grupo': postulaciones_sin_grupo,
    })


@login_required
@permiso_requerido('crear_oferta')
def crear_grupo(request, oferta_id):
    """Crear un nuevo grupo para una oferta (AJAX)."""
    if request.method == 'POST':
        try:
            oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
            
            grupo = GrupoOferta.objects.create(
                oferta=oferta,
                nombre_grupo=request.POST.get('nombre_grupo', '').strip().upper(),
                fecha_inicio=request.POST.get('fecha_inicio') or None,
                fecha_fin=request.POST.get('fecha_fin') or None,
                horario=request.POST.get('horario', '').strip() or None,
                lugar=request.POST.get('lugar', '').strip().upper() or None,
                instructor=request.POST.get('instructor', '').strip().upper() or None,
                cupo_maximo=request.POST.get('cupo_maximo', 20),
                creado_por=request.user.id,
                actualizado_por=request.user.id,
            )
            
            # Asignar trabajadores seleccionados al grupo
            trabajadores_ids = request.POST.getlist('trabajadores_ids[]')
            if trabajadores_ids:
                Postulacion.objects.filter(
                    oferta=oferta,
                    trabajador_id__in=trabajadores_ids,
                    estado='APROBADO_GH',
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
    
    # GET: Mostrar formulario
    oferta = get_object_or_404(OfertaFormacion, id=oferta_id)
    postulaciones_aprobadas = Postulacion.objects.filter(
        oferta=oferta,
        estado='APROBADO_GH',
        grupo__isnull=True
    ).select_related('trabajador__persona', 'trabajador__cargo_estructural')
    
    return render(request, 'planificacion/crear_grupo.html', {
        'oferta': oferta,
        'postulaciones': postulaciones_aprobadas,
    })


@login_required
@permiso_requerido('editar_oferta')
def editar_grupo(request, grupo_id):
    """Editar un grupo existente."""
    grupo = get_object_or_404(GrupoOferta.objects.select_related('oferta'), id=grupo_id)
    
    if request.method == 'POST':
        try:
            grupo.nombre_grupo = request.POST.get('nombre_grupo', grupo.nombre_grupo).strip().upper()
            grupo.fecha_inicio = request.POST.get('fecha_inicio') or grupo.fecha_inicio
            grupo.fecha_fin = request.POST.get('fecha_fin') or grupo.fecha_fin
            grupo.horario = request.POST.get('horario', '').strip() or grupo.horario
            grupo.lugar = request.POST.get('lugar', '').strip().upper() or grupo.lugar
            grupo.instructor = request.POST.get('instructor', '').strip().upper() or grupo.instructor
            grupo.cupo_maximo = request.POST.get('cupo_maximo', grupo.cupo_maximo)
            grupo.actualizado_por = request.user.id
            grupo.save()
            return JsonResponse({'success': True, 'mensaje': 'Grupo actualizado.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    participantes = Postulacion.objects.filter(
        grupo=grupo
    ).select_related('trabajador__persona')
    
    return render(request, 'planificacion/editar_grupo.html', {
        'grupo': grupo,
        'participantes': participantes,
    })