from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from datetime import date
from configuracion.models import (
    TipoDocIdentificacion, Sexo, EstadoCivil, 
    Estado, Municipio, Parroquia, Direccion
)
from .models import Persona, PersonaDireccion, Vivienda, PersonaVivienda

@login_required
def registro_paso1(request):
    if 'registro_persona_id' in request.session:
        del request.session['registro_persona_id']
    
    contexto = {
        'tipos_docs': TipoDocIdentificacion.objects.filter(esta_activo=True).order_by('sigla'),
        'sexos': Sexo.objects.filter(esta_activo=True).order_by('descripcion'),
        'estados_civiles': EstadoCivil.objects.filter(esta_activo=True).order_by('descripcion'),
    }
    return render(request, 'registro/datos_personales.html', contexto)

@login_required
@require_POST
def guardar_paso1(request):
    try:
        cedula = request.POST.get('cedula', '').strip()
        fecha_nac_str = request.POST.get('fecha_nacimiento')
        if not fecha_nac_str:
            return JsonResponse({'success': False, 'error': 'La fecha de nacimiento es obligatoria.'})
            
        fecha_nacimiento = date.fromisoformat(fecha_nac_str)
        hoy = date.today()
        edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
        
        if edad < 16:
            return JsonResponse({'success': False, 'error': f'El aspirante es menor de edad ({edad} años).'})

        if Persona.objects.filter(cedula=cedula).exists():
            return JsonResponse({'success': False, 'error': f'La cédula {cedula} ya está registrada.'})

        es_naturalizado = 'es_naturalizado' in request.POST
        nro_gaceta = None
        fecha_gaceta = None

        if es_naturalizado:
            nro_gaceta = request.POST.get('nro_gaceta', '').strip().upper()
            fecha_gaceta = request.POST.get('fecha_gaceta')
            if not nro_gaceta or not fecha_gaceta:
                return JsonResponse({'success': False, 'error': 'Datos de gaceta obligatorios.'})

        nueva_persona = Persona.objects.create(
            tipo_doc_identificacion_id = request.POST.get('tipo_doc'),
            cedula = cedula,
            primer_nombre = request.POST.get('nombre1', '').strip().upper(),
            segundo_nombre = request.POST.get('nombre2', '').strip().upper() or None,
            primer_apellido = request.POST.get('apellido1', '').strip().upper(),
            segundo_apellido = request.POST.get('apellido2', '').strip().upper() or None,
            fecha_nacimiento = fecha_nacimiento,
            lugar_nacimiento = request.POST.get('lugar_nacimiento', '').strip().upper(),
            sexo_id = request.POST.get('sexo'),
            estado_civil_id = request.POST.get('estado_civil'),
            es_naturalizado = es_naturalizado,
            nro_gaceta = nro_gaceta,
            fecha_gaceta = fecha_gaceta,
            creado_por = request.user.id,
            actualizado_por = request.user.id
        )
        
        request.session['registro_persona_id'] = nueva_persona.id
        return JsonResponse({'success': True, 'message': 'Paso 1 listo.', 'next_url': '/trabajadores/registro/paso-2/'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def registro_paso2(request):
    if 'registro_persona_id' not in request.session: return redirect('registro_paso1')
    contexto = {'estados': Estado.objects.filter(esta_activo=True).order_by('nombre_estado')}
    return render(request, 'registro/ubicacion_habitacion.html', contexto)

@login_required
@require_POST
def guardar_paso2(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        nueva_dir = Direccion.objects.create(
            parroquia_id = request.POST.get('parroquia'),
            direccion_exacta = request.POST.get('direccion_exacta', '').strip().upper(),
            creado_por = request.user.id
        )
        PersonaDireccion.objects.create(persona_id=persona_id, direccion_id=nueva_dir.id, es_principal=True, creado_por=request.user.id)
        return JsonResponse({'success': True, 'next_url': '/trabajadores/registro/paso-3/'})
    except Exception as e: return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_municipios(request, estado_id):
    municipios = Municipio.objects.filter(estado_id=estado_id, esta_activo=True).values('id', 'nombre_municipio').order_by('nombre_municipio')
    return JsonResponse(list(municipios), safe=False)

@login_required
def get_parroquias(request, municipio_id):
    parroquias = Parroquia.objects.filter(municipio_id=municipio_id, esta_activo=True).values('id', 'nombre_parroquia').order_by('nombre_parroquia')
    return JsonResponse(list(parroquias), safe=False)

@login_required
def registro_paso3(request):
    if 'registro_persona_id' not in request.session:
        return redirect('registro_paso1')
    
    # Importación segura
    from configuracion.models import TiposVivienda, CondicionesVivienda
    
    contexto = {
        'tipos_viviendas': TiposVivienda.objects.filter(esta_activo=True).order_by('descripcion'),
        'condiciones': CondicionesVivienda.objects.filter(esta_activo=True).order_by('descripcion'),
    }
    return render(request, 'registro/datos_viviendas.html', contexto)

@login_required
@require_POST
def guardar_paso3(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        ultima_dir_rel = PersonaDireccion.objects.filter(persona_id=persona_id, es_principal=True).last()
        
        if not ultima_dir_rel:
            return JsonResponse({'success': False, 'error': 'No se encontró la dirección.'})

        # 1. Crear el registro de la Vivienda con AMBOS campos
        nueva_vivienda = Vivienda.objects.create(
            direccion_id = ultima_dir_rel.direccion_id,
            tipo_vivienda_id = request.POST.get('tipo_vivienda'),
            condicion_vivienda_id = request.POST.get('condicion_vivienda'), # <--- Este es el que daba error
            creado_por = request.user.id
        )

        # 2. Vincular la persona con la vivienda
        PersonaVivienda.objects.create(
            persona_id = persona_id,
            vivienda_id = nueva_vivienda.id,
            creado_por = request.user.id
        )

        return JsonResponse({'success': True, 'next_url': '/trabajadores/registro/paso-4/'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# FUNCIONES TEMPORALES PARA EL PASO 4 (Evita el AttributeError)
@login_required
def registro_paso4(request):
    return JsonResponse({'message': 'Paso 4 próximamente'})

@login_required
def guardar_paso4(request):
    return JsonResponse({'success': True})