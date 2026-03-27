from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from datetime import date
# Importamos de ambas apps con cuidado
from configuracion.models import (
    TipoDocIdentificacion, Sexo, EstadoCivil, 
    Estado, Municipio, Parroquia, Direccion
)
from .models import Persona, PersonaDireccion

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

        # 1. Validación de Fecha de Nacimiento
        if not fecha_nac_str:
            return JsonResponse({'success': False, 'error': 'La fecha de nacimiento es obligatoria.'})
            
        fecha_nacimiento = date.fromisoformat(fecha_nac_str)
        hoy = date.today()
        edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
        
        if edad < 16:
            return JsonResponse({'success': False, 'error': f'El aspirante es menor de edad ({edad} años).'})

        # 2. Validación de Cédula Única
        if Persona.objects.filter(cedula=cedula).exists():
            return JsonResponse({'success': False, 'error': f'La cédula {cedula} ya está registrada.'})

        # 3. Procesar Naturalización (EL PUNTO CRÍTICO)
        es_naturalizado = 'es_naturalizado' in request.POST
        
        # Inicializamos como None (NULL en BD)
        nro_gaceta = None
        fecha_gaceta = None

        if es_naturalizado:
            nro_gaceta_raw = request.POST.get('nro_gaceta', '').strip().upper()
            fecha_gaceta_raw = request.POST.get('fecha_gaceta')

            if not nro_gaceta_raw or not fecha_gaceta_raw:
                return JsonResponse({'success': False, 'error': 'Si es naturalizado, el Nro. y la Fecha de Gaceta son obligatorios.'})
            
            nro_gaceta = nro_gaceta_raw
            fecha_gaceta = fecha_gaceta_raw

        # 4. Guardar Persona
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
            # Datos de naturalización corregidos
            es_naturalizado = es_naturalizado,
            nro_gaceta = nro_gaceta,
            fecha_gaceta = fecha_gaceta,
            creado_por = request.user.id,
            actualizado_por = request.user.id
        )
        
        request.session['registro_persona_id'] = nueva_persona.id
        return JsonResponse({
            'success': True, 
            'message': 'Paso 1 completado exitosamente.', 
            'next_url': '/trabajadores/registro/paso-2/'
        })

    except Exception as e:
        # Esto te imprimirá el error exacto en la consola para saber si es algo de la BD
        return JsonResponse({'success': False, 'error': f'Error: {str(e)}'})

@login_required
def registro_paso2(request):
    if 'registro_persona_id' not in request.session:
        return redirect('registro_paso1')
    
    contexto = {'estados': Estado.objects.filter(esta_activo=True).order_by('nombre_estado')}
    return render(request, 'registro/ubicacion_habitacion.html', contexto)

@login_required
@require_POST
def guardar_paso2(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        if not persona_id:
            return JsonResponse({'success': False, 'error': 'No hay una persona activa en el registro.'})

        # 1. Crear registro en tabla 'direcciones'
        nueva_dir = Direccion.objects.create(
            parroquia_id = request.POST.get('parroquia'),
            direccion_exacta = request.POST.get('direccion_exacta', '').strip().upper(),
            creado_por = request.user.id
        )

        # 2. Crear vínculo en 'personas_direcciones'
        PersonaDireccion.objects.create(
            persona_id = persona_id,
            direccion_id = nueva_dir.id,
            es_principal = True,
            creado_por = request.user.id
        )

        return JsonResponse({'success': True, 'message': 'Ubicación guardada.', 'next_url': '/trabajadores/registro/paso-3/'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# Auxiliares AJAX
@login_required
def get_municipios(request, estado_id):
    municipios = Municipio.objects.filter(estado_id=estado_id, esta_activo=True).values('id', 'nombre_municipio').order_by('nombre_municipio')
    return JsonResponse(list(municipios), safe=False)

@login_required
def get_parroquias(request, municipio_id):
    parroquias = Parroquia.objects.filter(municipio_id=municipio_id, esta_activo=True).values('id', 'nombre_parroquia').order_by('nombre_parroquia')
    return JsonResponse(list(parroquias), safe=False)