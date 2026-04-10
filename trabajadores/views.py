# =============================================================
# 1. IMPORTACIONES DE LIBRERÍAS ESTÁNDAR Y TERCEROS
# =============================================================
import json
import base64
import string
import random
import secrets
import os
from io import BytesIO
from datetime import date

import qrcode
from xhtml2pdf import pisa

# =============================================================
# 2. IMPORTACIONES DEL NÚCLEO DE DJANGO
# =============================================================
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import get_template
from django.contrib.auth.models import User # Por si lo usas para alguna validación extra
from django.forms.models import model_to_dict

# =============================================================
# 3. SEGURIDAD Y LÓGICA PERSONALIZADA (TU FUNCIÓN ROBUSTA)
# =============================================================
from seguridad.views import generar_clave_robusta

# =============================================================
# 4. MODELOS DEL SISTEMA (USANDO WILDCARD * PARA EFICIENCIA)
# =============================================================
# Nota: Al usar *, traemos todas las clases de una vez.
from configuracion.models import *
from seguridad.models import *
from .models import * # Estos son los modelos de la app 'trabajadores'

# --- PASO 1: DATOS PERSONALES ---
@login_required
def registro_paso1(request):
    if 'registro_persona_id' in request.session:
        del request.session['registro_persona_id']
    
    contexto = {
        'tipos_docs': TipoDocIdentificacion.objects.filter(
            esta_activo=True, 
            sigla__in=['V', 'E', 'P']
        ).order_by('sigla'),
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

        with transaction.atomic():
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
                es_naturalizado = 'es_naturalizado' in request.POST,
                nro_gaceta = request.POST.get('nro_gaceta', '').strip().upper() or None,
                fecha_gaceta = request.POST.get('fecha_gaceta') or None,
                creado_por = request.user.id,
                actualizado_por = request.user.id
            )
        
        request.session['registro_persona_id'] = nueva_persona.id
        return JsonResponse({'success': True, 'next_url': reverse('registro_paso2')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# --- PASO 2: UBICACIÓN Y ELECTORAL ---
@login_required
def registro_paso2(request):
    if 'registro_persona_id' not in request.session: return redirect('registro_paso1')
    contexto = {
        'estados': Estado.objects.filter(esta_activo=True).order_by('nombre_estado'),
        'tipos_viviendas': TiposVivienda.objects.filter(esta_activo=True).order_by('descripcion'),
        'condiciones': CondicionesVivienda.objects.filter(esta_activo=True).order_by('descripcion'),
    }
    return render(request, 'registro/ubicacion_vivienda_centrov.html', contexto)

@login_required
@require_POST
def guardar_paso2(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
        with transaction.atomic():
            nueva_dir = Direccion.objects.create(
                parroquia_id = request.POST.get('parroquia'),
                direccion_exacta = request.POST.get('direccion_exacta', '').strip().upper(),
                creado_por = user_id
            )
            PersonaDireccion.objects.create(persona_id=persona_id, direccion_id=nueva_dir.id, es_principal=True, creado_por=user_id)

            nueva_v = Vivienda.objects.create(
                direccion_id = nueva_dir.id,
                tipo_vivienda_id = request.POST.get('tipo_vivienda'),
                condicion_vivienda_id = request.POST.get('condicion_vivienda'),
                creado_por = user_id
            )
            PersonaVivienda.objects.create(persona_id=persona_id, vivienda_id=nueva_v.id, creado_por=user_id)

            centro_id = request.POST.get('centro_votacion_id')
            if centro_id:
                DatosElectorales.objects.update_or_create(
                    persona_id=persona_id,
                    defaults={'centro_votacion_id': centro_id, 'creado_por': user_id, 'actualizado_por': user_id}
                )

        return JsonResponse({'success': True, 'next_url': reverse('registro_paso3')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# --- PASO 3: CONTACTOS ---
@login_required
def registro_paso3(request):
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
        
    persona_id = request.session.get('registro_persona_id')
    
    # 🔍 PERSISTENCIA: Buscamos contactos y emergencias registrados
    contactos_existentes = PersonaContactoPersonal.objects.filter(
        persona_id=persona_id
    ).select_related('contacto_personal', 'contacto_personal__tipo_contacto')
    
    emergencias_existentes = PersonaContactoEmergencia.objects.filter(
        persona_id=persona_id
    ).select_related('contacto_emergencia')

    contexto = { 
        'tipos_contactos': TipoContacto.objects.filter(esta_activo=True).order_by('descripcion'),
        'contactos_existentes': contactos_existentes,
        'emergencias_existentes': emergencias_existentes,
    }
    return render(request, 'registro/contactos.html', contexto)

@login_required
@require_POST
def guardar_paso3(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
        # Capturamos los índices de los contactos marcados como principales
        indices_principales = json.loads(request.POST.get('indices_principales', '[]'))

        with transaction.atomic():
            # 🧹 LIMPIEZA: Borramos los vínculos anteriores de esta persona
            PersonaContactoPersonal.objects.filter(persona_id=persona_id).delete()
            PersonaContactoEmergencia.objects.filter(persona_id=persona_id).delete()

            # --- 1. GUARDAR CONTACTOS PERSONALES ---
            tipos_p = request.POST.getlist('tipo_contacto[]')
            valores_p = request.POST.getlist('valor_contacto[]')
            
            for i, (t, v) in enumerate(zip(tipos_p, valores_p)):
                if t and v:
                    valor_limpio = v.strip().lower()
                    
                    # 🚀 LÓGICA ANTIDUPLICADOS:
                    # Usamos update_or_create para que si el valor (teléfono/correo) ya existe,
                    # solo actualice el tipo o el rastro de auditoría, en lugar de intentar crearlo de nuevo.
                    c_personal, created = ContactoPersonal.objects.update_or_create(
                        valor_contacto=valor_limpio,
                        defaults={
                            'tipo_contacto_id': t,
                            'actualizado_por': user_id
                        }
                    )
                    
                    # 🔗 Creamos el vínculo con el trabajador
                    PersonaContactoPersonal.objects.create(
                        persona_id=persona_id,
                        contacto_personal_id=c_personal.id,
                        es_principal=(i in indices_principales),
                        creado_por=user_id
                    )

            # --- 2. GUARDAR CONTACTOS DE EMERGENCIA ---
            # (Aquí aplicamos lo mismo por seguridad, aunque suelen ser únicos por persona)
            nombres_e = request.POST.getlist('e_nombre[]')
            apellidos_e = request.POST.getlist('e_apellido[]')
            telefonos_e = request.POST.getlist('e_telefono[]')
            
            for n, a, tel in zip(nombres_e, apellidos_e, telefonos_e):
                if n and tel:
                    # Creamos el contacto de emergencia
                    c_emergencia = ContactoEmergencia.objects.create(
                        primer_nombre=n.strip().upper(),
                        primer_apellido=a.strip().upper(),
                        telefono=tel.strip(),
                        creado_por=user_id
                    )
                    # Vinculamos
                    PersonaContactoEmergencia.objects.create(
                        persona_id=persona_id,
                        contacto_emergencia_id=c_emergencia.id,
                        creado_por=user_id
                    )

        return JsonResponse({'success': True, 'next_url': reverse('registro_paso4')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# --- PASO 4: FORMACIÓN ACADÉMICA ---
@login_required
def registro_paso4(request):
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    persona_id = request.session.get('registro_persona_id')
    
    # 🔍 PERSISTENCIA: Buscamos estudios ya registrados
    academicos_existentes = FormacionAcademica.objects.filter(
        persona_id=persona_id,
        esta_activo=True
    ).select_related('nivel_formacion', 'estatus_formacion')

    contexto = {
        'niveles': NivelesFormacion.objects.filter(esta_activo=True).order_by('id'),
        'estatus': EstatusFormacion.objects.filter(esta_activo=True).order_by('id'),
        'academicos_existentes': academicos_existentes, # <--- Enviamos a la bandeja
    }
    return render(request, 'registro/formacion.html', contexto)

@login_required
@require_POST
def guardar_paso4(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
        niveles = request.POST.getlist('nivel_id[]')
        instituciones = request.POST.getlist('institucion[]')
        estatus_ids = request.POST.getlist('estatus_id[]')
        especialidades = request.POST.getlist('especialidad[]')
        fechas_inicio = request.POST.getlist('fecha_inicio[]')
        fechas_fin = request.POST.getlist('fecha_fin[]')

        posee_formacion_adicional = request.POST.get('ir_a_cursos') == 'true'

        with transaction.atomic():
            # 🧹 LIMPIEZA: Borramos lo anterior para que la lista nueva sea la que mande
            FormacionAcademica.objects.filter(persona_id=persona_id).delete()

            for i in range(len(niveles)):
                if niveles[i] and instituciones[i]:
                    FormacionAcademica.objects.create(
                        persona_id=persona_id, 
                        nivel_formacion_id=niveles[i],
                        estatus_formacion_id=estatus_ids[i],
                        institucion=instituciones[i].strip().upper(),
                        especialidad=especialidades[i].strip().upper() if especialidades[i] else None,
                        fecha_inicio=fechas_inicio[i] if fechas_inicio[i] and fechas_inicio[i] != 'None' else None,
                        fecha_fin=fechas_fin[i] if fechas_fin[i] and fechas_fin[i] != 'None' else None,
                        creado_por=user_id,
                        actualizado_por=user_id
                    )

        url_destino = reverse('registro_paso5') if posee_formacion_adicional else reverse('registro_paso6')
        return JsonResponse({'success': True, 'next_url': url_destino})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# --- PASO 5: ADIESTRAMIENTO ---
@login_required
def registro_paso5(request):
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    persona_id = request.session.get('registro_persona_id')
    
    # 🔍 PERSISTENCIA: Buscamos cursos ya registrados para esta persona
    cursos_guardados = FormacionAdicional.objects.filter(
        persona_id=persona_id, 
        esta_activo=True
    ).select_related('tipo_formacion', 'modalidad')

    contexto = {
        'tipos_formaciones': TipoFormacion.objects.filter(esta_activo=True).order_by('id'),
        'modalidades': Modalidad.objects.filter(esta_activo=True).order_by('id'),
        'cursos_existentes': cursos_guardados, # <--- Enviamos la lista al HTML
    }
    return render(request, 'registro/adiestramiento.html', contexto)

@login_required
@require_POST
def guardar_paso5(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
        # Capturamos las listas del HTML
        tipos = request.POST.getlist('tipo_formacion_id[]')
        nombres = request.POST.getlist('nombre_formacion_ad[]')
        instituciones = request.POST.getlist('institucion[]')
        modalidades = request.POST.getlist('modalidad_id[]')
        horas = request.POST.getlist('duracion_horas[]')
        fechas = request.POST.getlist('fecha_culminacion[]')

        with transaction.atomic():
            # 🧹 LIMPIEZA: Borramos las formaciones adicionales previas de esta persona
            # para que la nueva lista sea la definitiva (evita duplicados al re-guardar)
            FormacionAdicional.objects.filter(persona_id=persona_id).delete()

            for i in range(len(nombres)):
                if nombres[i] and instituciones[i] and tipos[i] and modalidades[i]:
                    FormacionAdicional.objects.create(
                        persona_id=persona_id, 
                        tipo_formacion_id=tipos[i],
                        modalidad_id=modalidades[i],
                        nombre_formacion_ad=nombres[i].strip().upper(),
                        institucion=instituciones[i].strip().upper(),
                        duracion_horas=horas[i] if horas[i] and horas[i] != 'None' else None,
                        fecha_culminacion=fechas[i] if fechas[i] and fechas[i] != 'None' else None,
                        creado_por=user_id, 
                        actualizado_por=user_id
                    )

        return JsonResponse({'success': True, 'next_url': reverse('registro_paso6')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# --- PASO 6: SALUD Y DISCAPACIDAD ---
@login_required
def registro_paso6(request):
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    persona_id = request.session.get('registro_persona_id')
    
    # 🔍 PERSISTENCIA: Buscamos los datos que ya existen
    salud_existente = PersonaSalud.objects.filter(persona_id=persona_id).first()
    patologias_existentes = PersonaPatologia.objects.filter(persona_id=persona_id).select_related('tipo_patologia')

    contexto = {
        'discapacidades': TipoDiscapacidad.objects.filter(esta_activo=True).order_by('descripcion'),
        'patologias': TipoPatologia.objects.filter(esta_activo=True).order_by('descripcion'),
        'salud': salud_existente,  # Datos únicos: Sangre, Alergias, Discapacidad
        'patologias_existentes': patologias_existentes, # Datos múltiples: Patologías
    }
    return render(request, 'registro/salud.html', contexto)

@login_required
@require_POST
def guardar_paso6(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
        with transaction.atomic():
            PersonaSalud.objects.update_or_create(
                persona_id=persona_id,
                defaults={
                    'tipo_sangre': request.POST.get('tipo_sangre'),
                    'nro_conapdis': request.POST.get('nro_conapdis', '').strip() or None,
                    'alergias': request.POST.get('alergias', '').strip().upper() or None,
                    'tipo_discapacidad_id': request.POST.get('discapacidad_id') or None,
                    'creado_por': user_id, 'actualizado_por': user_id
                }
            )

            patologias_ids = request.POST.getlist('patologia_id[]')
            detalles = request.POST.getlist('patologia_detalle[]')
            PersonaPatologia.objects.filter(persona_id=persona_id).delete()
            for pid, det in zip(patologias_ids, detalles):
                if pid:
                    PersonaPatologia.objects.create(
                        persona_id=persona_id, tipo_patologia_id=pid,
                        descripcion_adicional=det.strip().upper() or None, creado_por=user_id
                    )

        return JsonResponse({'success': True, 'next_url': reverse('registro_paso7')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# --- PASO 7: CARGA FAMILIAR ---
@login_required
def registro_paso7(request):
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    persona_id = request.session.get('registro_persona_id')
    persona = get_object_or_404(Persona, id=persona_id)
    
    # 🔍 PERSISTENCIA: Buscamos familiares ya registrados para este trabajador
    familiares_guardados = PersonaCargaFamiliar.objects.filter(
        persona_id=persona_id, 
        esta_activo=True
    ).select_related('carga_familiar', 'parentesco')

    # Filtro legal de parentescos según sexo del trabajador
    sexo_trabajador = persona.sexo.descripcion.upper()
    parentescos = Parentesco.objects.filter(esta_activo=True)
    
    if "FEMENINO" in sexo_trabajador:
        parentescos = parentescos.exclude(descripcion__icontains='ESPOSA')
    elif "MASCULINO" in sexo_trabajador:
        parentescos = parentescos.exclude(descripcion__icontains='ESPOSO')

    contexto = {
        'parentescos': parentescos.order_by('descripcion'),
        'sexos': Sexo.objects.filter(esta_activo=True).order_by('descripcion'),
        'familiares_existentes': familiares_guardados, # <--- Enviamos la lista al HTML
    }
    return render(request, 'registro/carga_familiar.html', contexto)

@login_required
@require_POST
def guardar_paso7(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
        # Capturamos las listas del formulario
        nombres1 = request.POST.getlist('f_nombre1[]')
        nombres2 = request.POST.getlist('f_nombre2[]')
        apellidos1 = request.POST.getlist('f_apellido1[]')
        apellidos2 = request.POST.getlist('f_apellido2[]')
        parentescos_ids = request.POST.getlist('f_parentesco_id[]')
        cedulas = request.POST.getlist('f_cedula[]')
        fechas_nac = request.POST.getlist('f_nacimiento[]')
        sexos_ids = request.POST.getlist('f_sexo[]')

        unicos_legales = ['MADRE', 'PADRE', 'ESPOSO', 'ESPOSA', 'CONYUGE']
        parentescos_enviados = []

        with transaction.atomic():
            # 🧹 LIMPIEZA: Borramos los VÍNCULOS anteriores de la persona.
            # No borramos a los familiares de la tabla global, solo la relación con este trabajador.
            from .models import PersonaCargaFamiliar, CargaFamiliar
            PersonaCargaFamiliar.objects.filter(persona_id=persona_id).delete()
            
            for i in range(len(nombres1)):
                if nombres1[i] and parentescos_ids[i]:
                    cedula_val = cedulas[i].strip() if i < len(cedulas) and cedulas[i] else None
                    
                    # Validación de parentesco único (Lógica del 30-03)
                    obj_p = Parentesco.objects.get(id=parentescos_ids[i])
                    desc_p = obj_p.descripcion.upper()
                    if desc_p in unicos_legales:
                        if desc_p in parentescos_enviados:
                            raise Exception(f"No puede registrar más de un(a) {desc_p}.")
                        parentescos_enviados.append(desc_p)

                    # 🚀 LÓGICA INTELIGENTE: Evitar el error de llave duplicada
                    if cedula_val:
                        # Si tiene cédula, usamos update_or_create para no chocar
                        familiar, created = CargaFamiliar.objects.update_or_create(
                            cedula=cedula_val,
                            defaults={
                                'primer_nombre': nombres1[i].strip().upper(),
                                'segundo_nombre': nombres2[i].strip().upper() if i < len(nombres2) else None,
                                'primer_apellido': apellidos1[i].strip().upper(),
                                'segundo_apellido': apellidos2[i].strip().upper() if i < len(apellidos2) else None,
                                'fecha_nacimiento': fechas_nac[i],
                                'sexo_id': sexos_ids[i],
                                'actualizado_por': user_id
                            }
                        )
                    else:
                        # Si es menor sin cédula, lo creamos directamente
                        familiar = CargaFamiliar.objects.create(
                            cedula=None,
                            primer_nombre=nombres1[i].strip().upper(),
                            segundo_nombre=nombres2[i].strip().upper() if i < len(nombres2) else None,
                            primer_apellido=apellidos1[i].strip().upper(),
                            segundo_apellido=apellidos2[i].strip().upper() if i < len(apellidos2) else None,
                            fecha_nacimiento=fechas_nac[i],
                            sexo_id=sexos_ids[i],
                            creado_por=user_id
                        )
                    
                    # 🔗 Creamos el nuevo vínculo con el trabajador
                    PersonaCargaFamiliar.objects.create(
                        persona_id=persona_id,
                        carga_familiar_id=familiar.id,
                        parentesco_id=parentescos_ids[i],
                        creado_por=user_id
                    )

        return JsonResponse({'success': True, 'next_url': reverse('registro_paso8')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# --- PASO 8: DATOS LABORALES ---
@login_required
def registro_paso8(request):
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    persona_id = request.session.get('registro_persona_id')
    
    # 🔍 PERSISTENCIA: Buscamos si el trabajador ya tiene datos registrados
    laboral_existente = Trabajador.objects.filter(persona_id=persona_id).first()

    contexto = {
        # Catálogos de Estructura (Nombres corregidos a singular según models.py)
        'sedes': Sede.objects.filter(esta_activo=True).order_by('nombre_sede'),
        'unidades': UnidadesOrganizativas.objects.filter(esta_activo=True).select_related('tipo_unidad').order_by('nombre_unidad'),
        'niveles_jer': NivelJerarquico.objects.filter(esta_activo=True).order_by('id'),
        
        # Catálogos Contractuales (Sincronizados con tus modelos)
        'categorias': CategoriaPersonal.objects.filter(esta_activo=True).order_by('id'),
        'tipos_trab': TiposTrabajadore.objects.filter(esta_activo=True).order_by('id'),
        'cargos_gen': CargosGenerico.objects.filter(esta_activo=True).order_by('nombre_cargo'),
        'cargos_est': CargosEstructural.objects.filter(esta_activo=True).order_by('nombre_cargo_estruct'),
        
        # Objeto para persistencia en el formulario
        'laboral': laboral_existente,
    }
    return render(request, 'registro/datos_laborales.html', contexto)

@login_required
@require_POST
def guardar_paso8(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
        # Extraemos y limpiamos el código de nómina
        cod_nomina = request.POST.get('codigo_nomina', '').strip().upper()

        with transaction.atomic():
            # 🚀 update_or_create: Si ya existe la persona en Trabajadores, actualiza.
            # Si no, crea el registro nuevo.
            Trabajador.objects.update_or_create(
                persona_id=persona_id,
                defaults={
                    'sede_id': request.POST.get('sede_id'),
                    'unidad_org_id': request.POST.get('unidad_id'),
                    'nivel_jerarquico_id': request.POST.get('nivel_id'),
                    'tipo_trabajador_id': request.POST.get('tipo_trabajador_id'),
                    'categoria_id': request.POST.get('categoria_id'),
                    'cargo_generico_id': request.POST.get('cargo_gen_id'),
                    'cargo_estructural_id': request.POST.get('cargo_est_id'),
                    'codigo_nomina': cod_nomina,
                    'fecha_ingreso_inst': request.POST.get('fecha_ingreso'),
                    'actualizado_por': user_id,
                }
            )
            
        return JsonResponse({'success': True, 'next_url': reverse('registro_paso9')})
        
    except Exception as e:
        # Manejo de error por si el código de nómina ya existe (llave única en DB)
        error_msg = str(e)
        if "codigo_nomina" in error_msg.lower():
            error_msg = "El código de nómina ingresado ya pertenece a otro trabajador."
        return JsonResponse({'success': False, 'error': error_msg})

def get_unidades_por_nivel(request):
    nivel_id = request.GET.get('nivel_id')
    # Traemos las unidades que pertenecen al nivel, 
    # ordenadas alfabéticamente para que el usuario las encuentre rápido.
    unidades = UnidadesOrganizativas.objects.filter(
        nivel_jerarquico_id=nivel_id, 
        esta_activo=True
    ).values('id', 'nombre_unidad')
    
    return JsonResponse(list(unidades), safe=False)

# --- PASO 9: CREDENCIALES Y FINALIZACIÓN ---
@login_required
def registro_paso9(request):
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    persona = get_object_or_404(Persona, id=request.session['registro_persona_id'])
    
    # BUSQUEDA EXACTA: Tipo que contenga 'CORREO' y que sea PRINCIPAL
    correo_obj = PersonaContactoPersonal.objects.filter(
        persona=persona, 
        es_principal=True, 
        contacto_personal__tipo_contacto__descripcion__icontains='CORREO'
    ).select_related('contacto_personal').first()
    
    # Si no hay principal, buscamos cualquier correo de esa persona
    if not correo_obj:
        correo_obj = PersonaContactoPersonal.objects.filter(
            persona=persona, 
            contacto_personal__tipo_contacto__descripcion__icontains='CORREO'
        ).select_related('contacto_personal').first()

    correo_electronico = correo_obj.contacto_personal.valor_contacto if correo_obj else "Sin correo registrado"
    
    # Generamos la clave aquí para mostrarla en el HTML y tenerla lista
    # Ejemplo: J12345678* (Inicial + Cédula + *)
    password_generada = f"{persona.primer_nombre[0].upper()}{persona.cedula}*"
    
    contexto = {
        'persona': persona, 
        'correo': correo_electronico,
        'password_generada': password_generada
    }
    
    return render(request, 'registro/finalizar.html', contexto)

@login_required
def registro_paso9(request):
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    persona = get_object_or_404(Persona, id=request.session['registro_persona_id'])
    
    # Buscamos los roles para el select
    roles = Rol.objects.filter(esta_activo=True).order_by('nombre_rol')
    
    # Tu búsqueda de correo principal
    correo_obj = PersonaContactoPersonal.objects.filter(
        persona=persona, 
        es_principal=True, 
        contacto_personal__tipo_contacto__descripcion__icontains='CORREO'
    ).select_related('contacto_personal').first()
    
    correo_electronico = correo_obj.contacto_personal.valor_contacto if correo_obj else "Sin correo registrado"
    
    # USAMOS TU FUNCIÓN ROBUSTA DE SEGURIDAD
    password_temporal = generar_clave_robusta(12)
    
    contexto = {
        'persona': persona, 
        'correo': correo_electronico,
        'password_generada': password_temporal,
        'roles': roles # <--- Mandamos los roles
    }
    return render(request, 'registro/finalizar.html', contexto)

@login_required
@require_POST
def finalizar_registro(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        persona = get_object_or_404(Persona, id=persona_id)
        trabajador = Trabajador.objects.get(persona=persona)
        
        # Datos del formulario
        email_destino = request.POST.get('email_envio')
        password_generada = request.POST.get('password_generada')
        crear_acceso = request.POST.get('crear_usuario') == 'true'
        rol_id = request.POST.get('rol_id')

        with transaction.atomic():
            if crear_acceso:
                # Verificamos si ya existe un usuario con esa cédula
                usuario_existente = Usuario.objects.filter(nombre_usuario=persona.cedula).first()
                
                if usuario_existente:
                    # CASO JADE: El usuario ya existe (Superusuario o previo)
                    # 1. Lo vinculamos a su ficha si no tiene trabajador_id asignado
                    if not usuario_existente.trabajador_id:
                        usuario_existente.trabajador_id = trabajador.id
                        usuario_existente.save()
                    
                    # 2. Preparamos el correo de notificación de vinculación
                    if email_destino and email_destino != "Sin correo registrado":
                        asunto = 'Actualización de Perfil - SACAT Almacenadora Caracas'
                        mensaje = (
                            f"Hola {persona.primer_nombre},\n\n"
                            f"Tu ficha de trabajador ha sido vinculada exitosamente a tu usuario existente.\n"
                            f"Usuario: {persona.cedula}\n\n"
                            "Ya puedes acceder al sistema con tus credenciales de siempre."
                        )
                        send_mail(asunto, mensaje, settings.EMAIL_HOST_USER, [email_destino])
                
                else:
                    # CASO NUEVO: El usuario no existe, se crea desde cero
                    Usuario.objects.create_user(
                        nombre_usuario=persona.cedula,
                        password=password_generada,
                        trabajador_id=trabajador.id,
                        rol_id=rol_id,
                        requiere_cambio_clave=True,
                        creado_por=request.user.id
                    )
                    
                    # Correo de bienvenida con la clave temporal generada
                    if email_destino and email_destino != "Sin correo registrado":
                        asunto = 'Bienvenido al SACAT - Almacenadora Caracas'
                        mensaje = (
                            f"Hola {persona.primer_nombre},\n\n"
                            f"Tu registro ha sido exitoso. Tus credenciales son:\n"
                            f"Usuario: {persona.cedula}\n"
                            f"Clave Temporal: {password_generada}\n\n"
                            "Por seguridad, el sistema te pedirá cambiar tu clave al ingresar."
                        )
                        send_mail(asunto, mensaje, settings.EMAIL_HOST_USER, [email_destino])

            # Limpiar la sesión siempre al finalizar con éxito
            if 'registro_persona_id' in request.session:
                del request.session['registro_persona_id']
            
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# --- AUXILIARES AJAX ---
@login_required
def get_municipios(request, estado_id):
    municipios = Municipio.objects.filter(estado_id=estado_id, esta_activo=True).values('id', 'nombre_municipio').order_by('nombre_municipio')
    return JsonResponse(list(municipios), safe=False)

@login_required
def get_parroquias(request, municipio_id):
    parroquias = Parroquia.objects.filter(municipio_id=municipio_id, esta_activo=True).values('id', 'nombre_parroquia').order_by('nombre_parroquia')
    return JsonResponse(list(parroquias), safe=False)


@login_required
def generar_pdf_ficha(request, persona_id):
    persona = get_object_or_404(Persona, id=persona_id)
    
    # 1. GENERACIÓN DEL CÓDIGO QR
    # Mantenemos tu lógica "criminal" que está excelente para la validación
    link_verificacion = request.build_absolute_uri('/') 
    datos_qr = (
        f"SACAT-ID: {persona.cedula}\n"
        f"Trabajador: {persona.primer_nombre} {persona.primer_apellido}\n"
        f"Validado por: {request.user.nombre_usuario}\n"
        f"Fecha: {date.today()}"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(datos_qr)
    qr.make(fit=True)
    
    img_qr = qr.make_image(fill_color="black", back_color="white")
    buffer_qr = BytesIO()
    img_qr.save(buffer_qr, format="PNG")
    qr_base64 = base64.b64encode(buffer_qr.getvalue()).decode()

    # 2. RECOLECCIÓN MAESTRA DE DATOS (Sincronizada con el nuevo Paso 8)
    # Aquí es donde ocurre la magia: traemos todas las relaciones de una vez
    datos_laborales = Trabajador.objects.filter(persona=persona).select_related(
        'sede', 
        'nivel_jerarquico', 
        'unidad_org', 
        'tipo_trabajador', 
        'categoria', 
        'cargo_generico', 
        'cargo_estructural'
    ).first()

    contexto = {
        'persona': persona,
        'qr_code': qr_base64,
        'hoy': date.today(),
        
        # Ubicación y Vivienda
        'direccion': PersonaDireccion.objects.filter(persona=persona, es_principal=True).select_related('direccion__parroquia__municipio__estado').first(),
        'vivienda': PersonaVivienda.objects.filter(persona=persona).select_related('vivienda__tipo_vivienda', 'vivienda__condicion_vivienda').first(),
        
        # Datos Electorales y Sociales
        'electoral': DatosElectorales.objects.filter(persona=persona).select_related('centro_votacion').first(),
        'salud': PersonaSalud.objects.filter(persona=persona).select_related('tipo_discapacidad').first(),
        'patologias': PersonaPatologia.objects.filter(persona=persona).select_related('tipo_patologia'),
        
        # Contactos
        'contactos': PersonaContactoPersonal.objects.filter(persona=persona).select_related('contacto_personal__tipo_contacto'),
        'emergencia': PersonaContactoEmergencia.objects.filter(persona=persona).select_related('contacto_emergencia').first(),
        
        # Formación y Familia
        'academicos': FormacionAcademica.objects.filter(persona=persona).select_related('nivel_formacion', 'estatus_formacion').order_by('-fecha_fin'),
        'cursos': FormacionAdicional.objects.filter(persona=persona).order_by('-fecha_culminacion'),
        'familia': PersonaCargaFamiliar.objects.filter(persona=persona).select_related('carga_familiar', 'parentesco'),
        
        # 🌟 DATA LABORAL COMPLETA 🌟
        'laboral': datos_laborales,
    }

    # 3. RENDERIZADO Y GENERACIÓN DEL PDF
    # Importante: verifica que la ruta del template sea exacta
    template = get_template('registro/ficha_trabajador_maestra.html')
    html = template.render(contexto)
    result = BytesIO()

    # Generamos el documento
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        # 'inline' para que se abra en el navegador, 'attachment' para que se descargue solo
        response['Content-Disposition'] = f'inline; filename="Ficha_{persona.cedula}.pdf"'
        return response
    
    return HttpResponse("Error crítico al generar la Ficha Técnica SACAT", status=400)



# =============================================================
# VERSION 2
# =============================================================

# --- AUXILIAR: VERIFICACIÓN DE UNICIDAD ---

@login_required
def verificar_cedula_ajax(request):
    cedula = request.GET.get('cedula', '').strip()
    persona = Persona.objects.filter(cedula=cedula).first()
    
    if persona:
        # Buscamos el archivo en la tabla Recaudo
        recaudo = Recaudo.objects.filter(trabajador__persona=persona, tipo_recaudo__descripcion__icontains='IDENTIDAD').first()
        url_archivo = recaudo.ruta_archivo.url if recaudo and recaudo.ruta_archivo else None

        data = {
            'exists': True,
            'persona': {
                'nombre1': persona.primer_nombre,
                'nombre2': persona.segundo_nombre or '',
                'apellido1': persona.primer_apellido,
                'apellido2': persona.segundo_apellido or '',
                'lugar_nacimiento': persona.lugar_nacimiento or '',
                'fecha_nacimiento': persona.fecha_nacimiento.isoformat() if persona.fecha_nacimiento else '',
                'vencimiento': persona.fecha_vencimiento_cedula.strftime('%m/%Y') if persona.fecha_vencimiento_cedula else '',
                'sexo': persona.sexo_id,
                'estado_civil': persona.estado_civil_id,
                'es_naturalizado': persona.es_naturalizado,
                'nro_gaceta': persona.nro_gaceta or '',
                'es_extraordinaria': 'true' if persona.es_extraordinaria else 'false',
                'fecha_gaceta': persona.fecha_gaceta.isoformat() if persona.fecha_gaceta else '',
                'url_archivo': url_archivo
            }
        }
        return JsonResponse(data)
    return JsonResponse({'exists': False})

# ==============================================================================
# FASE 1: REGISTRO INICIAL (RESPONSABILIDAD DE GESTIÓN HUMANA)
# ==============================================================================

# --- PASO 1: IDENTIDAD v2 ---
@login_required
def registro_paso1_v2(request):
    """Renderiza el formulario de identidad (Legal -> Personal)."""
    # Si iniciamos un registro nuevo, limpiamos la sesión del ID anterior
    if 'registro_persona_id' in request.session:
        del request.session['registro_persona_id']
    
    contexto = {
        # Traemos solo los necesarios. Sigla servirá para el label en el HTML
        'tipos_docs': TipoDocIdentificacion.objects.filter(esta_activo=True, sigla__in=['V', 'E', 'P']).order_by('sigla'),
        'sexos': Sexo.objects.filter(esta_activo=True).order_by('descripcion'),
        'estados_civiles': EstadoCivil.objects.filter(esta_activo=True).order_by('descripcion'),
    }
    return render(request, 'registrov2/fase1/paso1_identidad.html', contexto)

@login_required
@require_POST
def guardar_paso1_v2(request):
    import os
    """
    Versión Blindada v15: 
    - Guarda/Actualiza identidad.
    - Crea/Obtiene ficha laboral.
    - Sobreescribe físicamente el archivo digital (di_cedula) para evitar basura.
    """
    try:
        # --- 1. RECOLECCIÓN Y LIMPIEZA DE DATOS ---
        cedula = request.POST.get('cedula', '').strip()
        tipo_doc_id = request.POST.get('tipo_doc')
        vencimiento_raw = request.POST.get('fecha_vencimiento_id')
        fecha_nac_str = request.POST.get('fecha_nacimiento')
        
        if not all([cedula, tipo_doc_id, vencimiento_raw, fecha_nac_str]):
            return JsonResponse({'success': False, 'error': 'Existen campos obligatorios vacíos.'})

        # --- 2. VALIDACIONES DE REGLAS DE NEGOCIO ---
        tipo_doc = get_object_or_404(TipoDocIdentificacion, id=tipo_doc_id)
        
        if tipo_doc.sigla == 'E' and int(cedula) < 80000000:
            return JsonResponse({'success': False, 'error': 'Cédula extranjera debe ser mayor o igual a 80.000.000'})
        
        fecha_nacimiento = date.fromisoformat(fecha_nac_str)
        edad = (date.today() - fecha_nacimiento).days // 365
        if edad < 16:
            return JsonResponse({'success': False, 'error': f'El trabajador es menor de edad ({edad} años).'})

        try:
            mes, anio = vencimiento_raw.split('/')
            fecha_vencimiento = date(int(anio), int(mes), 1)
        except (ValueError, IndexError):
            return JsonResponse({'success': False, 'error': 'Formato de vencimiento inválido. Use MM/AAAA.'})

        # --- 3. PROCESO DE GUARDADO ATÓMICO ---
        with transaction.atomic():
            
            # A. GUARDAR/ACTUALIZAR PERSONA
            persona, created = Persona.objects.update_or_create(
                cedula=cedula,
                defaults={
                    'tipo_doc_identificacion_id': tipo_doc_id,
                    'primer_nombre': request.POST.get('nombre1', '').strip().upper(),
                    'segundo_nombre': request.POST.get('nombre2', '').strip().upper() or None,
                    'primer_apellido': request.POST.get('apellido1', '').strip().upper(),
                    'segundo_apellido': request.POST.get('apellido2', '').strip().upper() or None,
                    'fecha_nacimiento': fecha_nacimiento,
                    'lugar_nacimiento': request.POST.get('lugar_nacimiento', '').strip().upper(),
                    'sexo_id': request.POST.get('sexo'),
                    'estado_civil_id': request.POST.get('estado_civil'),
                    'es_naturalizado': 'es_naturalizado' in request.POST,
                    'nro_gaceta': request.POST.get('nro_gaceta', '').strip().upper() or None,
                    'es_extraordinaria': request.POST.get('es_extraordinaria') == 'true',
                    'fecha_gaceta': request.POST.get('fecha_gaceta') or None,
                    'fecha_vencimiento_cedula': fecha_vencimiento,
                    'actualizado_por': request.user.id
                }
            )
            if created: 
                persona.creado_por = request.user.id
                persona.save()

            # B. CREAR/OBTENER FICHA LABORAL
            trabajador, t_created = Trabajador.objects.get_or_create(
                persona=persona,
                defaults={
                    'fase_actual': 1,
                    'creado_por': request.user.id,
                    'codigo_nomina': f"TEMP-{persona.cedula}",
                    'fecha_ingreso_inst': date.today(),
                }
            )

            # C. GESTIÓN DEL ARCHIVO DIGITAL (SOBREESCRITURA REAL)
            archivo = request.FILES.get('archivo_cedula')
            if archivo:
                tipo_r = TipoRecaudo.objects.filter(descripcion__icontains='IDENTIDAD').first()
                if not tipo_r:
                    return JsonResponse({'success': False, 'error': 'Falta configurar el Tipo de Recaudo "IDENTIDAD".'})
                
                # Buscamos si ya existe un registro de este recaudo
                recaudo_existente = Recaudo.objects.filter(trabajador=trabajador, tipo_recaudo=tipo_r).first()

                if recaudo_existente:
                    # 🛡️ BORRADO FÍSICO: Si hay un archivo viejo en el disco, lo eliminamos
                    if recaudo_existente.ruta_archivo:
                        ruta_vieja = recaudo_existente.ruta_archivo.path
                        if os.path.isfile(ruta_vieja):
                            os.remove(ruta_vieja)
                    
                    # Actualizamos el registro con el nuevo archivo
                    recaudo_existente.ruta_archivo = archivo
                    recaudo_existente.actualizado_por = request.user.id
                    recaudo_existente.fecha_vencimiento = fecha_vencimiento
                    recaudo_existente.save()
                else:
                    # Si no existía el registro, lo creamos
                    Recaudo.objects.create(
                        trabajador=trabajador,
                        tipo_recaudo=tipo_r,
                        ruta_archivo=archivo,
                        actualizado_por=request.user.id,
                        fecha_vencimiento=fecha_vencimiento
                    )

        # --- 4. RESPUESTA EXITOSA ---
        request.session['registro_persona_id'] = persona.id
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': f"Falla técnica en SACAT: {str(e)}"})

# --- PASO 2: CONTACTOS v2 ---
@login_required
def registro_paso2_v2(request):
    """RRHH registra solo los medios necesarios para la emisión de credenciales."""
    if 'registro_persona_id' not in request.session: return redirect('registro_paso1_v2')
    
    persona_id = request.session.get('registro_persona_id')
    contactos = PersonaContactoPersonal.objects.filter(persona_id=persona_id).select_related('contacto_personal__tipo_contacto')
    
    contexto = { 
        'tipos_contactos': TipoContacto.objects.filter(esta_activo=True),
        'contactos_existentes': contactos
    }
    return render(request, 'registrov2/fase1/paso2_contactos.html', contexto)

@login_required
@require_POST
def guardar_paso2_v2(request):
    """Guarda la lista de contactos asegurando que el Correo sea capturado."""
    try:
        persona_id = request.session.get('registro_persona_id')
        tipos = request.POST.getlist('tipo_id[]')
        valores = request.POST.getlist('valor[]')
        principales = request.POST.getlist('es_principal[]')

        with transaction.atomic():
            PersonaContactoPersonal.objects.filter(persona_id=persona_id).delete()
            for t_id, val, pri in zip(tipos, valores, principales):
                contacto, _ = ContactoPersonal.objects.update_or_create(
                    valor_contacto=val.strip().lower(),
                    defaults={'tipo_contacto_id': t_id, 'actualizado_por': request.user.id}
                )
                PersonaContactoPersonal.objects.create(
                    persona_id=persona_id,
                    contacto_personal_id=contacto.id,
                    es_principal=(pri == 'true'),
                    creado_por=request.user.id
                )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# --- PASO 3: ASIGNACIÓN LABORAL v2 ---
@login_required
def registro_paso3_v2(request):
    """Asignación de sede, nivel y unidad con soporte para jerarquía dinámica."""
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1_v2')
    
    persona_id = request.session.get('registro_persona_id')
    laboral = Trabajador.objects.filter(persona_id=persona_id).first()

    contexto = {
        'sedes': Sede.objects.filter(esta_activo=True).order_by('nombre_sede'),
        'niveles': NivelJerarquico.objects.filter(esta_activo=True).order_by('id'),
        'categorias': CategoriaPersonal.objects.filter(esta_activo=True),
        'tipos_trab': TiposTrabajadore.objects.filter(esta_activo=True),
        'cargos_gen': CargosGenerico.objects.filter(esta_activo=True).order_by('nombre_cargo'),
        # Cargamos los estructurales iniciales (solo universales por defecto para no saturar)
        'cargos_est': CargosEstructural.objects.filter(esta_activo=True).order_by('nombre_cargo_estruct'),
        'laboral': laboral
    }
    return render(request, 'registrov2/fase1/paso3_laboral.html', contexto)

@login_required
def get_unidades_v2(request):
    """Filtra unidades organizativas por SEDE, NIVEL o UNIDAD SUPERIOR."""
    sede_id = request.GET.get('sede_id')
    nivel_id = request.GET.get('nivel_id')
    superior_id = request.GET.get('superior_id')

    filtros = {'esta_activo': True}
    
    if sede_id and sede_id != "":
        filtros['sede_id'] = sede_id

    if superior_id and superior_id != "":
        # Buscamos hijos de una unidad específica (ej. Divisiones de una Gerencia)
        filtros['unidad_superior_id'] = superior_id
    elif nivel_id and nivel_id != "":
        # Carga inicial del nivel (Gerencias)
        filtros['nivel_jerarquico_id'] = nivel_id
    else:
        return JsonResponse([], safe=False)

    unidades = UnidadesOrganizativas.objects.filter(**filtros).order_by('nombre_unidad').values('id', 'nombre_unidad')
    return JsonResponse(list(unidades), safe=False)

@login_required
def get_unidades_v2(request):
    """
    Helper AJAX corregido para el SACAT.
    Muestra las unidades del nivel seleccionado sin importar si tienen superior,
    para que oficinas como la OTIC (Apoyo) aparezcan de una vez.
    """
    sede_id = request.GET.get('sede_id')
    nivel_id = request.GET.get('nivel_id')
    superior_id = request.GET.get('superior_id') # Para buscar Divisiones/Coordinaciones

    filtros = {'esta_activo': True}

    if superior_id and superior_id != "":
        # ESCENARIO A: Buscamos los "hijos" (Divisiones o Coordinaciones)
        # Aquí sí filtramos por el superior seleccionado
        filtros['unidad_sup_id'] = superior_id
    elif nivel_id and nivel_id != "":
        # ESCENARIO B: Carga inicial de la Gerencia/Oficina
        # Filtramos por Nivel y Sede, pero QUITAMOS el filtro de 'isnull'
        # para que aparezcan todas las oficinas de ese nivel (OTIC, OGHU, etc.)
        filtros['nivel_jerarquico_id'] = nivel_id
        if sede_id and sede_id != "":
            filtros['sede_id'] = sede_id
    else:
        return JsonResponse([], safe=False)

    # Nota: Usamos 'unidad_sup_id' que es el nombre real en tu .sql
    unidades = UnidadesOrganizativas.objects.filter(**filtros).order_by('nombre_unidad').values('id', 'nombre_unidad')
    
    return JsonResponse(list(unidades), safe=False)

@login_required
@require_POST
def guardar_paso3_v2(request):
    """Finaliza la carga de datos de RRHH asegurando la última unidad seleccionada."""
    try:
        persona_id = request.session.get('registro_persona_id')
        if not persona_id:
            return JsonResponse({'success': False, 'error': 'Sesión no válida.'})
            
        # El ID de la unidad viene del último select con valor en el frontend
        unidad_id = request.POST.get('unidad_id')

        with transaction.atomic():
            Trabajador.objects.update_or_create(
                persona_id=persona_id,
                defaults={
                    'sede_id': request.POST.get('sede_id'),
                    'unidad_org_id': unidad_id,
                    'nivel_jerarquico_id': request.POST.get('nivel_id'),
                    'tipo_trabajador_id': request.POST.get('tipo_trabajador_id'),
                    'categoria_id': request.POST.get('categoria_id'),
                    'cargo_generico_id': request.POST.get('cargo_gen_id'),
                    'cargo_estructural_id': request.POST.get('cargo_est_id'),
                    'codigo_nomina': request.POST.get('codigo_nomina', '').strip().upper() or None,
                    'fecha_ingreso_inst': request.POST.get('fecha_ingreso'),
                    'fase_actual': 1,
                    'actualizado_por': request.user.id
                }
            )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f"Error en SACAT: {str(e)}"})

# --- PASO 4: COMPROBANTE Y EMISIÓN v2 (REFORZADO) ---
@login_required
def paso4_comprobante_v1(request):
    """Genera la clave y prepara el resumen final con jerarquía y nivel."""
    persona_id = request.session.get('registro_persona_id')
    if not persona_id: return redirect('registro_paso1_v2')
    
    persona = get_object_or_404(Persona, id=persona_id)
    trabajador = get_object_or_404(Trabajador, persona=persona)
    
    # 1. Recuperar Contactos (Principal)
    correo_obj = PersonaContactoPersonal.objects.filter(
        persona=persona, es_principal=True, 
        contacto_personal__tipo_contacto__descripcion__icontains='CORREO'
    ).select_related('contacto_personal').first()
    
    tlf_obj = PersonaContactoPersonal.objects.filter(
        persona=persona, es_principal=True, 
        contacto_personal__tipo_contacto__descripcion__icontains='TELEFONO'
    ).select_related('contacto_personal').first()

    # 2. MOTOR DE JERARQUÍA SINCERADA
    u_final = trabajador.unidad_org 
    u_n1, u_n2, u_n3 = None, None, None

    if u_final.unidad_sup: 
        padre = u_final.unidad_sup
        if padre.unidad_sup: 
            u_n1 = padre.unidad_sup
            u_n2 = padre
            u_n3 = u_final
        else: 
            u_n1 = padre
            u_n2 = u_final
    else: 
        u_n1 = u_final

    # 3. EXTRAER EL NIVEL JERÁRQUICO (Lo que nos faltaba)
    # Lo sacamos de u_n1 porque es la unidad raíz que define el nivel (Superior, Apoyo, etc.)
    nombre_nivel = "NO DEFINIDO"
    if u_n1 and u_n1.nivel_jerarquico:
        nombre_nivel = u_n1.nivel_jerarquico.descripcion

    if 'temp_pass' not in request.session:
        request.session['temp_pass'] = generar_clave_robusta(12) 
        
    contexto = {
        'persona': persona,
        'laboral': trabajador,
        'u_n1': u_n1, 
        'u_n2': u_n2, 
        'u_n3': u_n3,
        'nivel_jerarquico': nombre_nivel, # <--- ¡Aquí está el dato!
        'correo_principal': correo_obj.contacto_personal.valor_contacto if correo_obj else "N/A",
        'telefono_principal': tlf_obj.contacto_personal.valor_contacto if tlf_obj else "N/A",
        'password_generada': request.session['temp_pass'],
    }
    return render(request, 'registrov2/fase1/paso4_comprobante.html', contexto)

@login_required
@require_POST
def finalizar_fase1_v2(request):
    """Cierra la fase 1, crea usuario y guarda la ficha en el expediente."""
    try:
        persona_id = request.session.get('registro_persona_id')
        persona = Persona.objects.get(id=persona_id)
        trabajador = Trabajador.objects.get(persona=persona)
        password_temp = request.session.get('temp_pass')

        with transaction.atomic():
            # 1. Crear Usuario (Rol 3 = Trabajador Fase 2)
            Usuario.objects.create_user(
                nombre_usuario=persona.cedula,
                password=password_temp,
                trabajador_id=trabajador.id,
                rol_id=3,
                requiere_cambio_clave=True,
                creado_por=request.user.id
            )

            # 2. LOGICA DE RECAUDO: Guardar Ficha Inicial en Carpeta
            # Usamos la misma ruta definida en el Paso 1
            folder_path = os.path.join('expedientes', persona.cedula, 'recaudos')
            full_path = os.path.join(settings.MEDIA_ROOT, folder_path)
            if not os.path.exists(full_path): os.makedirs(full_path)

            # --- Aquí llamarías a tu función de generar PDF ---
            # Supongamos que genera un archivo llamado ficha_inicial.pdf
            nombre_archivo = f"FICHA_INICIAL_{persona.cedula}.pdf"
            ruta_db = os.path.join(folder_path, nombre_archivo)
            
            # 3. Registrar en Tabla Recaudos
            # Buscamos o creamos el tipo de recaudo
            tipo_rec, _ = Recaudo.objects.get_or_create(nombre_recaudo='FICHA INICIAL')
            
            RecaudosTrabajador.objects.update_or_create(
                trabajador=trabajador,
                recaudo=tipo_rec,
                defaults={
                    'archivo_path': ruta_db,
                    'esta_validado': True,
                    'creado_por': request.user.id
                }
            )

            # 4. Promover a Fase 2
            trabajador.fase_actual = 2
            trabajador.save()
            
            del request.session['registro_persona_id']
            del request.session['temp_pass']
            
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

import os
import base64
import qrcode
from io import BytesIO
from datetime import date
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from xhtml2pdf import pisa

# Asegúrate de importar tus modelos (Persona, Trabajador, PersonaContactoPersonal) aquí arriba

@login_required
def generar_ficha_inicial_v2(request, persona_id):
    """
    Genera la Ficha Técnica Inicial en PDF con cintillo institucional desde MEDIA.
    """
    # 1. Recuperar los objetos
    persona = get_object_or_404(Persona, id=persona_id)
    laboral = Trabajador.objects.filter(persona=persona).first()

    if not laboral:
        return HttpResponse(f"Error: No se encontró ficha laboral para la CI {persona.cedula}.", status=404)

    # 2. MOTOR DE JERARQUÍA (Desglose de niveles)
    u_final = laboral.unidad_org
    u_n1, u_n2, u_n3 = None, None, None

    if u_final:
        if u_final.unidad_sup: 
            padre = u_final.unidad_sup
            if padre.unidad_sup: 
                u_n1 = padre.unidad_sup
                u_n2 = padre
                u_n3 = u_final
            else: 
                u_n1 = padre
                u_n2 = u_final
        else: 
            u_n1 = u_final

    # Definición del Nivel Jerárquico
    nombre_nivel = "NO DEFINIDO"
    if u_n1 and u_n1.nivel_jerarquico:
        nombre_nivel = u_n1.nivel_jerarquico.descripcion
    elif laboral.nivel_jerarquico:
        nombre_nivel = laboral.nivel_jerarquico.descripcion

    # 3. CONTACTOS
    contactos = PersonaContactoPersonal.objects.filter(persona=persona).select_related('contacto_personal__tipo_contacto')

    # 4. QR DE SEGURIDAD
    datos_qr = (
        f"SACAT - VALIDACION FASE 1\n"
        f"CI: {persona.cedula}\n"
        f"UNIDAD: {u_n1.nombre_unidad if u_n1 else 'N/A'}\n"
        f"FECHA: {date.today().strftime('%d/%m/%Y')}"
    )
    qr = qrcode.make(datos_qr)
    buf_qr = BytesIO()
    qr.save(buf_qr, format="PNG")
    qr_b64 = base64.b64encode(buf_qr.getvalue()).decode()

    # 5. CARGA DEL CINTILLO DESDE MEDIA
    cintillo_path = os.path.join(settings.MEDIA_ROOT, 'cintillo_almccs.png')
    cintillo_b64 = ""
    if os.path.exists(cintillo_path):
        with open(cintillo_path, "rb") as f:
            cintillo_b64 = base64.b64encode(f.read()).decode()

    # 6. CONTEXTO PARA EL TEMPLATE
    contexto = {
        'persona': persona,
        'laboral': laboral,
        'u_n1': u_n1, 
        'u_n2': u_n2, 
        'u_n3': u_n3,
        'nivel_nombre': nombre_nivel,
        'contactos': contactos,
        'qr_code': qr_b64,
        'cintillo': cintillo_b64,
        'hoy': date.today(),
    }

    # 7. GENERACIÓN DEL PDF
    template = get_template('registrov2/fase1/ficha_inicial_trabajadores.html')
    html_content = template.render(contexto)
    result = BytesIO()
    
    pdf = pisa.pisaDocument(BytesIO(html_content.encode("UTF-8")), result)

    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Ficha_{persona.cedula}.pdf"'
        return response
    
    return HttpResponse("Error en generación de PDF", status=400)