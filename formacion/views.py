from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

# 🆕 Importamos el decorador personalizado de permisos
from seguridad.decorators import permiso_requerido

from .models import OfertaFormacion, Postulacion
from configuracion.models import TipoFormacion, Modalidad
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

@login_required
@permiso_requerido('ver_bandeja_aprobacion')  # 🆕
def bandeja_aprobacion(request):
    """
    Muestra las postulaciones según el rol del usuario:
    - Jefe: postulaciones de trabajadores de su misma unidad.
    - GH: todas las postulaciones aprobadas por jefes.
    """
    user = request.user
    rol = user.rol.nombre_rol.upper() if user.rol else ''

    trabajador_user = Trabajador.objects.filter(persona__cedula=user.nombre_usuario).first()

    postulaciones_jefe = []
    postulaciones_gh = []
    es_jefe = False
    es_gh = ('GESTION' in rol or 'ADMINISTRADOR' in rol or 'SUPERUSUARIO' in rol)

    if trabajador_user and trabajador_user.unidad_org:
        es_jefe = True
        postulaciones_jefe = Postulacion.objects.filter(
            trabajador__unidad_org=trabajador_user.unidad_org,
            estado='PENDIENTE'
        ).select_related('trabajador__persona', 'oferta').order_by('-fecha_postulacion')

    if es_gh:
        postulaciones_gh = Postulacion.objects.filter(
            estado='APROBADO_JEFE'
        ).select_related('trabajador__persona', 'oferta').order_by('-fecha_postulacion')

    return render(request, 'aprobacion/bandeja_aprobacion.html', {
        'postulaciones_jefe': postulaciones_jefe,
        'postulaciones_gh': postulaciones_gh,
        'es_jefe': es_jefe,
        'es_gh': es_gh,
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