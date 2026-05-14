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
import requests
import re
from bs4 import BeautifulSoup

# =============================================================
# 2. IMPORTACIONES DEL NÚCLEO DE DJANGO
# =============================================================
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import get_template
from django.contrib.auth.models import User
from django.forms.models import model_to_dict

# =============================================================
# 3. SEGURIDAD Y LÓGICA PERSONALIZADA
# =============================================================
from seguridad.views import generar_clave_robusta

# 🆕 Importamos el decorador personalizado de permisos
from seguridad.decorators import permiso_requerido

# =============================================================
# 4. MODELOS DEL SISTEMA
# =============================================================
from configuracion.models import *
from seguridad.models import *
from .models import *


# =============================================================================
# FUNCIONES AUXILIARES AJAX (USO EN FORMULARIOS - ACCESO GENERAL)
# =============================================================================

@login_required
def get_municipios(request, estado_id):
    """Retorna municipios por estado (uso en formularios de registro)."""
    municipios = Municipio.objects.filter(estado_id=estado_id, esta_activo=True).values('id', 'nombre_municipio').order_by('nombre_municipio')
    return JsonResponse(list(municipios), safe=False)


@login_required
def get_parroquias(request, municipio_id):
    """Retorna parroquias por municipio (uso en formularios de registro)."""
    parroquias = Parroquia.objects.filter(municipio_id=municipio_id, esta_activo=True).values('id', 'nombre_parroquia').order_by('nombre_parroquia')
    return JsonResponse(list(parroquias), safe=False)


def get_centros_por_parroquia(request, parroquia_id):
    """Retorna centros de votación por parroquia (uso en formularios)."""
    centros = CentroVotacion.objects.filter(parroquia_id=parroquia_id, esta_activo=True).values('id', 'nombre_centro').order_by('nombre_centro')
    return JsonResponse(list(centros), safe=False)


@login_required
def get_unidades_por_nivel(request):
    """Retorna unidades por nivel jerárquico (uso en formularios)."""
    nivel_id = request.GET.get('nivel_id')
    unidades = UnidadesOrganizativas.objects.filter(
        nivel_jerarquico_id=nivel_id, 
        esta_activo=True
    ).values('id', 'nombre_unidad')
    return JsonResponse(list(unidades), safe=False)


@login_required
def get_unidades_v2(request):
    """Filtra unidades organizativas por SEDE, NIVEL o UNIDAD SUPERIOR (v2)."""
    sede_id = request.GET.get('sede_id')
    nivel_id = request.GET.get('nivel_id')
    superior_id = request.GET.get('superior_id')

    filtros = {'esta_activo': True}

    if superior_id and superior_id != "":
        filtros['unidad_sup_id'] = superior_id
    elif nivel_id and nivel_id != "":
        filtros['nivel_jerarquico_id'] = nivel_id
        if sede_id and sede_id != "":
            filtros['sede_id'] = sede_id
    else:
        return JsonResponse([], safe=False)

    unidades = UnidadesOrganizativas.objects.filter(**filtros).order_by('nombre_unidad').values('id', 'nombre_unidad')
    return JsonResponse(list(unidades), safe=False)


# =============================================================================
# CONSULTA SENIAT/PNP (ACCESO GENERAL PARA REGISTRO)
# =============================================================================

URL_BASE_PNP = "https://www.sistemaspnp.com/cedula/"
URL_RESULTADO_PNP = "https://www.sistemaspnp.com/cedula/resultado.php"


def obtener_captcha_seniat(request):
    """Función de compatibilidad para que el urls.py no chille."""
    return JsonResponse({'success': True})


@login_required
@permiso_requerido('consultar_seniat')  # 🆕
def consultar_datos_seniat(request):
    """
    IA SACAT: Resuelve la suma y extrae los datos usando la estructura 
    de etiquetas <p> y <strong> del portal.
    """
    cedula = request.GET.get('cedula', '').strip()
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': URL_BASE_PNP
    }

    try:
        res_inicio = session.get(URL_BASE_PNP, headers=headers, timeout=10, verify=False)
        soup_inicio = BeautifulSoup(res_inicio.text, 'html.parser')
        
        label_captcha = soup_inicio.find('label', class_='captcha-question')
        if not label_captcha:
            return JsonResponse({'success': False, 'error': 'No se pudo leer el captcha del portal.'})

        numeros = re.findall(r'\d+', label_captcha.get_text())
        if len(numeros) >= 2:
            resultado_suma = int(numeros[0]) + int(numeros[1])
        else:
            return JsonResponse({'success': False, 'error': 'Formato de suma no reconocido.'})

        payload = {
            'cedula': cedula,
            'captcha': resultado_suma,
            'enviar': 'Consultar'
        }
        
        res_final = session.post(URL_RESULTADO_PNP, data=payload, headers=headers, timeout=10, verify=False)
        soup_res = BeautifulSoup(res_final.text, 'html.parser')

        p_tags = soup_res.find_all('p')
        extraido = {}
        
        for p in p_tags:
            strong = p.find('strong')
            if strong:
                clave = strong.get_text().replace(":", "").strip()
                valor = p.get_text().replace(strong.get_text(), "").strip()
                extraido[clave] = valor

        if "Primer Apellido" in extraido:
            nombres_lista = extraido.get("Nombres", "").split()
            
            return JsonResponse({
                'success': True,
                'sugerencia': {
                    'apellido1': extraido.get("Primer Apellido", ""),
                    'apellido2': extraido.get("Segundo Apellido", ""),
                    'nombre1': nombres_lista[0] if len(nombres_lista) > 0 else '',
                    'nombre2': " ".join(nombres_lista[1:]) if len(nombres_lista) > 1 else ''
                }
            })
        
        return JsonResponse({'success': False, 'error': 'Cédula no encontrada o captcha fallido.'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': f"Error de conexión: {str(e)}"})


# =============================================================================
# LISTADO Y CONSULTA DE TRABAJADORES (GESTIÓN HUMANA)
# =============================================================================

@login_required
@permiso_requerido('ver_listado_trabajadores')  # 🆕
def listar_trabajadores(request):
    """Listado general de trabajadores."""
    busqueda = request.GET.get('search', '')
    
    trabajadores = Trabajador.objects.select_related(
        'persona', 
        'persona__sexo', 
        'unidad_org', 
        'cargo_estructural'
    ).all()

    if busqueda:
        trabajadores = trabajadores.filter(
            Q(persona__cedula__icontains=busqueda) |
            Q(persona__primer_nombre__icontains=busqueda) |
            Q(persona__primer_apellido__icontains=busqueda)
        )

    hoy = date.today()
    for t in trabajadores:
        if t.persona.fecha_nacimiento:
            fn = t.persona.fecha_nacimiento
            t.edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
        else:
            t.edad = "N/A"

    contexto = {
        'trabajadores': trabajadores,
        'busqueda': busqueda,
    }
    return render(request, 'listado/listar_trabajadores.html', contexto)


@login_required
@permiso_requerido('ver_detalle_trabajador')  # 🆕
def detalle_trabajador_json(request, trabajador_id):
    """Retorna los datos del trabajador para el modal del listado SACAT."""
    try:
        t = get_object_or_404(
            Trabajador.objects.select_related('persona', 'unidad_org', 'cargo_estructural', 'sede'), 
            id=trabajador_id
        )
        
        data = {
            'nombre_completo': f"{t.persona.primer_nombre} {t.persona.primer_apellido}",
            'cedula': t.persona.cedula,
            'cargo': t.cargo_estructural.nombre_cargo_estruct.upper() if t.cargo_estructural else "N/A",
            'unidad': t.unidad_org.nombre_unidad.upper() if t.unidad_org else "N/A",
            'sede': t.sede.nombre_sede.upper() if t.sede else "N/A",
            'ingreso': t.fecha_ingreso_inst.strftime('%d/%m/%Y') if t.fecha_ingreso_inst else "N/A",
            'nomina': t.codigo_nomina,
            'persona_id': t.persona.id
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@permiso_requerido('ver_perfil_trabajador')  # 🆕
def perfil_trabajador(request, trabajador_id):
    """Expediente completo del trabajador."""
    t = get_object_or_404(
        Trabajador.objects.select_related(
            'persona', 'persona__sexo', 'persona__estado_civil',
            'unidad_org', 'cargo_estructural', 'sede', 'nivel_jerarquico',
            'tipo_trabajador', 'categoria', 'cargo_generico'
        ), id=trabajador_id
    )
    p = t.persona

    hoy = date.today()
    nacimiento = p.fecha_nacimiento
    edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day)) if nacimiento else None

    direccion = PersonaDireccion.objects.filter(persona=p, es_principal=True).select_related('direccion__parroquia__municipio__estado').first()
    vivienda = PersonaVivienda.objects.filter(persona=p).select_related('vivienda__tipo_vivienda', 'vivienda__condicion_vivienda').first()
    electoral = DatosElectorales.objects.filter(persona=p).select_related('centro_votacion').first()
    contactos = PersonaContactoPersonal.objects.filter(persona=p).select_related('contacto_personal__tipo_contacto')
    emergencia = PersonaContactoEmergencia.objects.filter(persona=p).select_related('contacto_emergencia').first()
    academicos = FormacionAcademica.objects.filter(persona=p, esta_activo=True).select_related('nivel_formacion', 'estatus_formacion').order_by('-fecha_fin')
    cursos = FormacionAdicional.objects.filter(persona=p, esta_activo=True).order_by('-fecha_culminacion')
    salud = PersonaSalud.objects.filter(persona=p).select_related('tipo_discapacidad').first()
    patologias = PersonaPatologia.objects.filter(persona=p, esta_activo=True).select_related('tipo_patologia')
    familia = PersonaCargaFamiliar.objects.filter(persona=p, esta_activo=True).select_related('carga_familiar', 'parentesco')
    recaudos = Recaudo.objects.filter(trabajador=t, esta_activo=True).select_related('tipo_recaudo')
    experiencias = ExperienciaPrevia.objects.filter(trabajador=t, esta_activo=True)
    dotaciones = Dotacion.objects.filter(trabajador=t, esta_activo=True).select_related('talla_dotacion__item_dotacion')
    contacto_inst = ContactoInstitucional.objects.filter(trabajador=t).first()

    contexto = {
        't': t, 'p': p, 'edad': edad,
        'direccion': direccion, 'vivienda': vivienda, 'electoral': electoral,
        'contactos': contactos, 'emergencia': emergencia,
        'academicos': academicos, 'cursos': cursos,
        'salud': salud, 'patologias': patologias, 'familia': familia,
        'recaudos': recaudos, 'experiencias': experiencias, 'dotaciones': dotaciones,
        'contacto_inst': contacto_inst,
    }
    return render(request, 'listado/perfil_trabajador.html', contexto)


@login_required
@permiso_requerido('verificar_cedula')  # 🆕
def verificar_cedula_ajax(request):
    """Verificar si una cédula ya existe en el sistema."""
    cedula = request.GET.get('cedula', '').strip()
    persona = Persona.objects.filter(cedula=cedula).first()
    
    if persona:
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


# =============================================================================
# REGISTRO DE TRABAJADORES - FLUJO V1 (9 PASOS)
# =============================================================================

@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
def registro_paso1(request):
    """Paso 1: Datos personales."""
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
@permiso_requerido('registrar_trabajador_f1')  # 🆕
@require_POST
def guardar_paso1(request):
    """Guardar datos personales del trabajador."""
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

        persona_existente = Persona.objects.filter(cedula=cedula).first()
        
        if persona_existente:
            request.session['registro_persona_id'] = persona_existente.id
            
            trabajador = Trabajador.objects.filter(persona=persona_existente).first()
            if trabajador:
                usuario = Usuario.objects.filter(trabajador=trabajador).first()
                
                if usuario:
                    clave_temporal = generar_clave_robusta() 
                    
                    with transaction.atomic():
                        usuario.set_password(clave_temporal)
                        usuario.requiere_cambio_clave = True
                        usuario.save()

                    correo_obj = PersonaContactoPersonal.objects.filter(
                        persona=persona_existente, 
                        contacto_personal__tipo_contacto__descripcion__icontains='CORREO'
                    ).select_related('contacto_personal').first()

                    if correo_obj:
                        email_destino = correo_obj.contacto_personal.valor_contacto
                        asunto = 'Restablecimiento de Acceso - SACAT'
                        mensaje = f"""
                        Hola {persona_existente.primer_nombre}, 
                        Detectamos que ya posees un registro en el sistema. 
                        Tus credenciales han sido restablecidas:
                        
                        Usuario: {persona_existente.cedula}
                        Nueva Clave Temporal: {clave_temporal}
                        
                        Ingresa al sistema para completar o actualizar tu expediente.
                        """
                        send_mail(asunto, mensaje, settings.EMAIL_HOST_USER, [email_destino])
                        
                        return JsonResponse({
                            'success': True, 
                            'info': 'Cédula registrada anteriormente. Se enviaron nuevas credenciales a su correo.',
                            'next_url': reverse('inicio')
                        })

            return JsonResponse({
                'success': True, 
                'info': 'Continuando con el registro iniciado anteriormente.',
                'next_url': reverse('registro_paso2')
            })

        with transaction.atomic():
            nueva_persona = Persona.objects.create(
                tipo_doc_identificacion_id=request.POST.get('tipo_doc'),
                cedula=cedula,
                primer_nombre=request.POST.get('nombre1', '').strip().upper(),
                segundo_nombre=request.POST.get('nombre2', '').strip().upper() or None,
                primer_apellido=request.POST.get('apellido1', '').strip().upper(),
                segundo_apellido=request.POST.get('apellido2', '').strip().upper() or None,
                fecha_nacimiento=fecha_nacimiento,
                lugar_nacimiento=request.POST.get('lugar_nacimiento', '').strip().upper(),
                sexo_id=request.POST.get('sexo'),
                estado_civil_id=request.POST.get('estado_civil'),
                es_naturalizado='es_naturalizado' in request.POST,
                nro_gaceta=request.POST.get('nro_gaceta', '').strip().upper() or None,
                fecha_gaceta=request.POST.get('fecha_gaceta') or None,
                creado_por=request.user.id,
                actualizado_por=request.user.id
            )
        
        request.session['registro_persona_id'] = nueva_persona.id
        return JsonResponse({'success': True, 'next_url': reverse('registro_paso2')})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
def registro_paso2(request):
    """Paso 2: Ubicación y electoral."""
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    contexto = {
        'estados': Estado.objects.filter(esta_activo=True).order_by('nombre_estado'),
        'tipos_viviendas': TiposVivienda.objects.filter(esta_activo=True).order_by('descripcion'),
        'condiciones': CondicionesVivienda.objects.filter(esta_activo=True).order_by('descripcion'),
    }
    return render(request, 'registro/ubicacion_vivienda_centrov.html', contexto)


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
@require_POST
def guardar_paso2(request):
    """Guardar ubicación y datos electorales."""
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
        with transaction.atomic():
            nueva_dir = Direccion.objects.create(
                parroquia_id=request.POST.get('parroquia'),
                direccion_exacta=request.POST.get('direccion_exacta', '').strip().upper(),
                creado_por=user_id
            )
            PersonaDireccion.objects.create(persona_id=persona_id, direccion_id=nueva_dir.id, es_principal=True, creado_por=user_id)

            nueva_v = Vivienda.objects.create(
                direccion_id=nueva_dir.id,
                tipo_vivienda_id=request.POST.get('tipo_vivienda'),
                condicion_vivienda_id=request.POST.get('condicion_vivienda'),
                creado_por=user_id
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


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
def registro_paso3(request):
    """Paso 3: Contactos."""
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
        
    persona_id = request.session.get('registro_persona_id')
    
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
@permiso_requerido('registrar_trabajador_f1')  # 🆕
@require_POST
def guardar_paso3(request):
    """Guardar contactos personales y de emergencia."""
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
        indices_principales = json.loads(request.POST.get('indices_principales', '[]'))

        with transaction.atomic():
            PersonaContactoPersonal.objects.filter(persona_id=persona_id).delete()
            PersonaContactoEmergencia.objects.filter(persona_id=persona_id).delete()

            tipos_p = request.POST.getlist('tipo_contacto[]')
            valores_p = request.POST.getlist('valor_contacto[]')
            
            for i, (t, v) in enumerate(zip(tipos_p, valores_p)):
                if t and v:
                    valor_limpio = v.strip().lower()
                    c_personal, created = ContactoPersonal.objects.update_or_create(
                        valor_contacto=valor_limpio,
                        defaults={
                            'tipo_contacto_id': t,
                            'actualizado_por': user_id
                        }
                    )
                    PersonaContactoPersonal.objects.create(
                        persona_id=persona_id,
                        contacto_personal_id=c_personal.id,
                        es_principal=(i in indices_principales),
                        creado_por=user_id
                    )

            nombres_e = request.POST.getlist('e_nombre[]')
            apellidos_e = request.POST.getlist('e_apellido[]')
            telefonos_e = request.POST.getlist('e_telefono[]')
            
            for n, a, tel in zip(nombres_e, apellidos_e, telefonos_e):
                if n and tel:
                    c_emergencia = ContactoEmergencia.objects.create(
                        primer_nombre=n.strip().upper(),
                        primer_apellido=a.strip().upper(),
                        telefono=tel.strip(),
                        creado_por=user_id
                    )
                    PersonaContactoEmergencia.objects.create(
                        persona_id=persona_id,
                        contacto_emergencia_id=c_emergencia.id,
                        creado_por=user_id
                    )

        return JsonResponse({'success': True, 'next_url': reverse('registro_paso4')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
def registro_paso4(request):
    """Paso 4: Formación académica."""
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    persona_id = request.session.get('registro_persona_id')
    
    academicos_existentes = FormacionAcademica.objects.filter(
        persona_id=persona_id, esta_activo=True
    ).select_related('nivel_formacion', 'estatus_formacion')

    contexto = {
        'niveles': NivelesFormacion.objects.filter(esta_activo=True).order_by('id'),
        'estatus': EstatusFormacion.objects.filter(esta_activo=True).order_by('id'),
        'academicos_existentes': academicos_existentes,
    }
    return render(request, 'registro/formacion.html', contexto)


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
@require_POST
def guardar_paso4(request):
    """Guardar formación académica."""
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
                        creado_por=user_id, actualizado_por=user_id
                    )

        url_destino = reverse('registro_paso5') if posee_formacion_adicional else reverse('registro_paso6')
        return JsonResponse({'success': True, 'next_url': url_destino})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
def registro_paso5(request):
    """Paso 5: Adiestramiento / Cursos."""
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    persona_id = request.session.get('registro_persona_id')
    
    cursos_guardados = FormacionAdicional.objects.filter(
        persona_id=persona_id, esta_activo=True
    ).select_related('tipo_formacion', 'modalidad')

    contexto = {
        'tipos_formaciones': TipoFormacion.objects.filter(esta_activo=True).order_by('id'),
        'modalidades': Modalidad.objects.filter(esta_activo=True).order_by('id'),
        'cursos_existentes': cursos_guardados,
    }
    return render(request, 'registro/adiestramiento.html', contexto)


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
@require_POST
def guardar_paso5(request):
    """Guardar adiestramiento / cursos."""
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
        tipos = request.POST.getlist('tipo_formacion_id[]')
        nombres = request.POST.getlist('nombre_formacion_ad[]')
        instituciones = request.POST.getlist('institucion[]')
        modalidades = request.POST.getlist('modalidad_id[]')
        horas = request.POST.getlist('duracion_horas[]')
        fechas = request.POST.getlist('fecha_culminacion[]')

        with transaction.atomic():
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
                        creado_por=user_id, actualizado_por=user_id
                    )

        return JsonResponse({'success': True, 'next_url': reverse('registro_paso6')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
def registro_paso6(request):
    """Paso 6: Salud y discapacidad."""
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    persona_id = request.session.get('registro_persona_id')
    
    salud_existente = PersonaSalud.objects.filter(persona_id=persona_id).first()
    patologias_existentes = PersonaPatologia.objects.filter(persona_id=persona_id).select_related('tipo_patologia')

    contexto = {
        'discapacidades': TipoDiscapacidad.objects.filter(esta_activo=True).order_by('descripcion'),
        'patologias': TipoPatologia.objects.filter(esta_activo=True).order_by('descripcion'),
        'salud': salud_existente,
        'patologias_existentes': patologias_existentes,
    }
    return render(request, 'registro/salud.html', contexto)


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
@require_POST
def guardar_paso6(request):
    """Guardar datos de salud."""
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


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
def registro_paso7(request):
    """Paso 7: Carga familiar."""
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    persona_id = request.session.get('registro_persona_id')
    persona = get_object_or_404(Persona, id=persona_id)
    
    familiares_guardados = PersonaCargaFamiliar.objects.filter(
        persona_id=persona_id, esta_activo=True
    ).select_related('carga_familiar', 'parentesco')

    sexo_trabajador = persona.sexo.descripcion.upper()
    parentescos = Parentesco.objects.filter(esta_activo=True)
    
    if "FEMENINO" in sexo_trabajador:
        parentescos = parentescos.exclude(descripcion__icontains='ESPOSA')
    elif "MASCULINO" in sexo_trabajador:
        parentescos = parentescos.exclude(descripcion__icontains='ESPOSO')

    contexto = {
        'parentescos': parentescos.order_by('descripcion'),
        'sexos': Sexo.objects.filter(esta_activo=True).order_by('descripcion'),
        'familiares_existentes': familiares_guardados,
    }
    return render(request, 'registro/carga_familiar.html', contexto)


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
@require_POST
def guardar_paso7(request):
    """Guardar carga familiar."""
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
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
            PersonaCargaFamiliar.objects.filter(persona_id=persona_id).delete()
            
            for i in range(len(nombres1)):
                if nombres1[i] and parentescos_ids[i]:
                    cedula_val = cedulas[i].strip() if i < len(cedulas) and cedulas[i] else None
                    
                    obj_p = Parentesco.objects.get(id=parentescos_ids[i])
                    desc_p = obj_p.descripcion.upper()
                    if desc_p in unicos_legales:
                        if desc_p in parentescos_enviados:
                            raise Exception(f"No puede registrar más de un(a) {desc_p}.")
                        parentescos_enviados.append(desc_p)

                    if cedula_val:
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
                    
                    PersonaCargaFamiliar.objects.create(
                        persona_id=persona_id,
                        carga_familiar_id=familiar.id,
                        parentesco_id=parentescos_ids[i],
                        creado_por=user_id
                    )

        return JsonResponse({'success': True, 'next_url': reverse('registro_paso8')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
def registro_paso8(request):
    """Paso 8: Datos laborales."""
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    persona_id = request.session.get('registro_persona_id')
    laboral_existente = Trabajador.objects.filter(persona_id=persona_id).first()

    contexto = {
        'sedes': Sede.objects.filter(esta_activo=True).order_by('nombre_sede'),
        'unidades': UnidadesOrganizativas.objects.filter(esta_activo=True).select_related('tipo_unidad').order_by('nombre_unidad'),
        'niveles_jer': NivelJerarquico.objects.filter(esta_activo=True).order_by('id'),
        'categorias': CategoriaPersonal.objects.filter(esta_activo=True).order_by('id'),
        'tipos_trab': TiposTrabajadore.objects.filter(esta_activo=True).order_by('id'),
        'cargos_gen': CargosGenerico.objects.filter(esta_activo=True).order_by('nombre_cargo'),
        'cargos_est': CargosEstructural.objects.filter(esta_activo=True).order_by('nombre_cargo_estruct'),
        'laboral': laboral_existente,
    }
    return render(request, 'registro/datos_laborales.html', contexto)


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
@require_POST
def guardar_paso8(request):
    """Guardar datos laborales."""
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        cod_nomina = request.POST.get('codigo_nomina', '').strip().upper()

        with transaction.atomic():
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
        error_msg = str(e)
        if "codigo_nomina" in error_msg.lower():
            error_msg = "El código de nómina ingresado ya pertenece a otro trabajador."
        return JsonResponse({'success': False, 'error': error_msg})


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
def registro_paso9(request):
    """Paso 9: Credenciales y finalización."""
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    persona = get_object_or_404(Persona, id=request.session['registro_persona_id'])
    roles = Rol.objects.filter(esta_activo=True).order_by('nombre_rol')
    
    correo_obj = PersonaContactoPersonal.objects.filter(
        persona=persona, 
        es_principal=True, 
        contacto_personal__tipo_contacto__descripcion__icontains='CORREO'
    ).select_related('contacto_personal').first()
    
    correo_electronico = correo_obj.contacto_personal.valor_contacto if correo_obj else "Sin correo registrado"
    password_temporal = generar_clave_robusta(12)
    
    contexto = {
        'persona': persona, 
        'correo': correo_electronico,
        'password_generada': password_temporal,
        'roles': roles
    }
    return render(request, 'registro/finalizar.html', contexto)


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
@require_POST
def finalizar_registro(request):
    """Finalizar registro y crear usuario."""
    try:
        persona_id = request.session.get('registro_persona_id')
        persona = get_object_or_404(Persona, id=persona_id)
        trabajador = Trabajador.objects.get(persona=persona)
        
        email_destino = request.POST.get('email_envio')
        password_generada = request.POST.get('password_generada')
        crear_acceso = request.POST.get('crear_usuario') == 'true'
        rol_id = request.POST.get('rol_id')

        with transaction.atomic():
            if crear_acceso:
                usuario_existente = Usuario.objects.filter(nombre_usuario=persona.cedula).first()
                
                if usuario_existente:
                    if not usuario_existente.trabajador_id:
                        usuario_existente.trabajador_id = trabajador.id
                        usuario_existente.save()
                    
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
                    Usuario.objects.create_user(
                        nombre_usuario=persona.cedula,
                        password=password_generada,
                        trabajador_id=trabajador.id,
                        rol_id=rol_id,
                        requiere_cambio_clave=True,
                        creado_por=request.user.id
                    )
                    
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

            if 'registro_persona_id' in request.session:
                del request.session['registro_persona_id']
            
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# =============================================================================
# REGISTRO DE TRABAJADORES - FLUJO V2 (FASE 1 - RRHH)
# =============================================================================

@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
def registro_paso1_v2(request):
    """Fase 1 - Paso 1 v2: Identidad."""
    if 'registro_persona_id' in request.session:
        del request.session['registro_persona_id']
    
    contexto = {
        'tipos_docs': TipoDocIdentificacion.objects.filter(esta_activo=True, sigla__in=['V', 'E', 'P']).order_by('sigla'),
        'sexos': Sexo.objects.filter(esta_activo=True).order_by('descripcion'),
        'estados_civiles': EstadoCivil.objects.filter(esta_activo=True).order_by('descripcion'),
    }
    return render(request, 'registrov2/fase1/paso1_identidad.html', contexto)


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
@require_POST
def guardar_paso1_v2(request):
    """Guardar identidad v2."""
    try:
        cedula = request.POST.get('cedula', '').strip()
        tipo_doc_id = request.POST.get('tipo_doc')
        vencimiento_raw = request.POST.get('fecha_vencimiento_id')
        fecha_nac_str = request.POST.get('fecha_nacimiento')
        
        if not all([cedula, tipo_doc_id, vencimiento_raw, fecha_nac_str]):
            return JsonResponse({'success': False, 'error': 'Existen campos obligatorios vacíos.'})

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

        with transaction.atomic():
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

            trabajador, t_created = Trabajador.objects.get_or_create(
                persona=persona,
                defaults={
                    'fase_actual': 1,
                    'creado_por': request.user.id,
                    'codigo_nomina': f"TEMP-{persona.cedula}",
                    'fecha_ingreso_inst': date.today(),
                }
            )

            archivo = request.FILES.get('archivo_cedula')
            if archivo:
                tipo_r = TipoRecaudo.objects.filter(descripcion__icontains='IDENTIDAD').first()
                if not tipo_r:
                    return JsonResponse({'success': False, 'error': 'Falta configurar el Tipo de Recaudo "IDENTIDAD".'})
                
                recaudo_existente = Recaudo.objects.filter(trabajador=trabajador, tipo_recaudo=tipo_r).first()

                if recaudo_existente:
                    if recaudo_existente.ruta_archivo:
                        ruta_vieja = recaudo_existente.ruta_archivo.path
                        if os.path.isfile(ruta_vieja):
                            os.remove(ruta_vieja)
                    
                    recaudo_existente.ruta_archivo = archivo
                    recaudo_existente.actualizado_por = request.user.id
                    recaudo_existente.fecha_vencimiento = fecha_vencimiento
                    recaudo_existente.save()
                else:
                    Recaudo.objects.create(
                        trabajador=trabajador,
                        tipo_recaudo=tipo_r,
                        ruta_archivo=archivo,
                        actualizado_por=request.user.id,
                        fecha_vencimiento=fecha_vencimiento
                    )

        request.session['registro_persona_id'] = persona.id
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': f"Falla técnica en SACAT: {str(e)}"})


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
def registro_paso2_v2(request):
    """Fase 1 - Paso 2 v2: Contactos."""
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1_v2')
    
    persona_id = request.session.get('registro_persona_id')
    contactos = PersonaContactoPersonal.objects.filter(
        persona_id=persona_id
    ).select_related('contacto_personal__tipo_contacto')
    
    contexto = { 
        'tipos_contactos': TipoContacto.objects.filter(esta_activo=True),
        'contactos_guardados': contactos
    }
    return render(request, 'registrov2/fase1/paso2_contactos.html', contexto)


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
@require_POST
def guardar_paso2_v2(request):
    """Guardar contactos v2."""
    try:
        persona_id = request.session.get('registro_persona_id')
        if not persona_id:
            return JsonResponse({'success': False, 'error': 'Sesión expirada. Vuelva al Paso 1.'})

        contactos_ids = request.POST.getlist('contacto_id[]') 
        tipos = request.POST.getlist('tipo_id[]')
        valores = request.POST.getlist('valor[]')
        principales = request.POST.getlist('es_principal[]')

        ids_correos = list(TipoContacto.objects.filter(
            descripcion__icontains='CORREO', esta_activo=True
        ).values_list('id', flat=True))

        tiene_email_principal = False
        for t_id, pri in zip(tipos, principales):
            if int(t_id) in ids_correos and str(pri).lower() == 'true':
                tiene_email_principal = True
                break
        
        if not tiene_email_principal:
            return JsonResponse({'success': False, 'error': 'Requisito SACAT: Se requiere un Correo Electrónico marcado como PRINCIPAL.'})

        with transaction.atomic():
            PersonaContactoPersonal.objects.filter(persona_id=persona_id).delete()
            
            for c_id, t_id, val, pri in zip(contactos_ids, tipos, valores, principales):
                valor_limpio = val.strip().lower()
                if not valor_limpio:
                    continue

                if c_id and c_id != 'None' and c_id != '':
                    contacto = ContactoPersonal.objects.get(id=c_id)
                    contacto.valor_contacto = valor_limpio
                    contacto.tipo_contacto_id = t_id
                    contacto.actualizado_por = request.user.id
                    contacto.save()
                else:
                    contacto, _ = ContactoPersonal.objects.update_or_create(
                        valor_contacto=valor_limpio,
                        defaults={
                            'tipo_contacto_id': t_id, 
                            'actualizado_por': request.user.id
                        }
                    )
                
                PersonaContactoPersonal.objects.create(
                    persona_id=persona_id,
                    contacto_personal_id=contacto.id,
                    es_principal=(str(pri).lower() == 'true'),
                    creado_por=request.user.id
                )
                
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': f"Error en Motor SACAT: {str(e)}"})


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
def registro_paso3_v2(request):
    """Fase 1 - Paso 3 v2: Asignación laboral."""
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
        'cargos_est': CargosEstructural.objects.filter(esta_activo=True).order_by('nombre_cargo_estruct'),
        'laboral': laboral
    }
    return render(request, 'registrov2/fase1/paso3_laboral.html', contexto)


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
@require_POST
def guardar_paso3_v2(request):
    """Guardar asignación laboral v2."""
    try:
        persona_id = request.session.get('registro_persona_id')
        if not persona_id:
            return JsonResponse({'success': False, 'error': 'Sesión no válida.'})
            
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


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
def paso4_comprobante_v1(request):
    """Fase 1 - Paso 4 v2: Comprobante y emisión."""
    persona_id = request.session.get('registro_persona_id')
    if not persona_id: 
        return redirect('registro_paso1_v2')
    
    persona = get_object_or_404(Persona, id=persona_id)
    trabajador = get_object_or_404(Trabajador, persona=persona)
    
    correo_obj = PersonaContactoPersonal.objects.filter(
        persona=persona, es_principal=True, 
        contacto_personal__tipo_contacto__descripcion__icontains='CORREO'
    ).select_related('contacto_personal').first()
    
    tlf_obj = PersonaContactoPersonal.objects.filter(
        persona=persona, es_principal=True, 
        contacto_personal__tipo_contacto__descripcion__icontains='TELEFONO'
    ).select_related('contacto_personal').first()

    u_final = trabajador.unidad_org 
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

    nombre_nivel = "NO DEFINIDO"
    if u_n1 and u_n1.nivel_jerarquico:
        nombre_nivel = u_n1.nivel_jerarquico.descripcion

    roles = Rol.objects.filter(esta_activo=True).order_by('nombre_rol')

    if 'temp_pass' not in request.session:
        request.session['temp_pass'] = generar_clave_robusta(12) 
        
    contexto = {
        'persona': persona,
        'laboral': trabajador,
        'u_n1': u_n1, 'u_n2': u_n2, 'u_n3': u_n3,
        'nivel_jerarquico': nombre_nivel,
        'correo_principal': correo_obj.contacto_personal.valor_contacto if correo_obj else "N/A",
        'telefono_principal': tlf_obj.contacto_personal.valor_contacto if tlf_obj else "N/A",
        'password_generada': request.session['temp_pass'],
        'roles': roles,
    }
    return render(request, 'registrov2/fase1/paso4_comprobante.html', contexto)


@login_required
@permiso_requerido('registrar_trabajador_f1')  # 🆕
@require_POST
def finalizar_fase1_v2(request):
    """Finalizar fase 1 y crear usuario."""
    try:
        persona_id = request.session.get('registro_persona_id')
        persona = Persona.objects.get(id=persona_id)
        trabajador = Trabajador.objects.get(persona=persona)
        password_temp = request.session.get('temp_pass')
        rol_id = request.POST.get('rol_id')

        with transaction.atomic():
            usuario, creado = Usuario.objects.update_or_create(
                nombre_usuario=persona.cedula,
                defaults={
                    'trabajador_id': trabajador.id,
                    'rol_id': rol_id,
                    'requiere_cambio_clave': True,
                    'actualizado_por': request.user.id
                }
            )
            usuario.set_password(password_temp)
            usuario.save()

            correo_obj = PersonaContactoPersonal.objects.filter(
                persona=persona, 
                contacto_personal__tipo_contacto__descripcion__icontains='CORREO'
            ).select_related('contacto_personal').first()

            if correo_obj:
                email_destino = correo_obj.contacto_personal.valor_contacto
                asunto = 'Acceso al Sistema SACAT'
                mensaje = f"""
                Hola {persona.primer_nombre}, 
                
                Se ha finalizado su registro en el sistema. 
                Sus credenciales de acceso son:
                Usuario: {persona.cedula}
                Clave Temporal: {password_temp}
                
                El sistema le solicitará cambio de clave al ingresar.
                """
                send_mail(asunto, mensaje, settings.EMAIL_HOST_USER, [email_destino])

            trabajador.fase_actual = 2
            trabajador.save()

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': f"Error en envío/cierre: {str(e)}"})


# =============================================================================
# GENERACIÓN DE PDFs (GESTIÓN HUMANA)
# =============================================================================

@login_required
@permiso_requerido('generar_ficha_inicial')  # 🆕
def generar_pdf_ficha(request, persona_id):
    """Generar PDF de ficha técnica (v1)."""
    persona = get_object_or_404(Persona, id=persona_id)
    
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

    datos_laborales = Trabajador.objects.filter(persona=persona).select_related(
        'sede', 'nivel_jerarquico', 'unidad_org', 
        'tipo_trabajador', 'categoria', 'cargo_generico', 'cargo_estructural'
    ).first()

    contexto = {
        'persona': persona, 'qr_code': qr_base64, 'hoy': date.today(),
        'direccion': PersonaDireccion.objects.filter(persona=persona, es_principal=True).select_related('direccion__parroquia__municipio__estado').first(),
        'vivienda': PersonaVivienda.objects.filter(persona=persona).select_related('vivienda__tipo_vivienda', 'vivienda__condicion_vivienda').first(),
        'electoral': DatosElectorales.objects.filter(persona=persona).select_related('centro_votacion').first(),
        'salud': PersonaSalud.objects.filter(persona=persona).select_related('tipo_discapacidad').first(),
        'patologias': PersonaPatologia.objects.filter(persona=persona).select_related('tipo_patologia'),
        'contactos': PersonaContactoPersonal.objects.filter(persona=persona).select_related('contacto_personal__tipo_contacto'),
        'emergencia': PersonaContactoEmergencia.objects.filter(persona=persona).select_related('contacto_emergencia').first(),
        'academicos': FormacionAcademica.objects.filter(persona=persona).select_related('nivel_formacion', 'estatus_formacion').order_by('-fecha_fin'),
        'cursos': FormacionAdicional.objects.filter(persona=persona).order_by('-fecha_culminacion'),
        'familia': PersonaCargaFamiliar.objects.filter(persona=persona).select_related('carga_familiar', 'parentesco'),
        'laboral': datos_laborales,
    }

    template = get_template('registro/ficha_trabajador_maestra.html')
    html = template.render(contexto)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Ficha_{persona.cedula}.pdf"'
        return response
    
    return HttpResponse("Error crítico al generar la Ficha Técnica SACAT", status=400)


@login_required
@permiso_requerido('generar_ficha_inicial')  # 🆕
def generar_ficha_inicial_v2(request, persona_id):
    """Generar PDF de ficha técnica inicial (v2) con cintillo institucional."""
    persona = get_object_or_404(Persona, id=persona_id)
    laboral = Trabajador.objects.filter(persona=persona).first()

    if not laboral:
        return HttpResponse(f"Error: No se encontró ficha laboral para la CI {persona.cedula}.", status=404)

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

    nombre_nivel = "NO DEFINIDO"
    if u_n1 and u_n1.nivel_jerarquico:
        nombre_nivel = u_n1.nivel_jerarquico.descripcion
    elif laboral.nivel_jerarquico:
        nombre_nivel = laboral.nivel_jerarquico.descripcion

    contactos = PersonaContactoPersonal.objects.filter(persona=persona).select_related('contacto_personal__tipo_contacto')

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

    cintillo_path = os.path.join(settings.MEDIA_ROOT, 'cintillo_almccs.png')
    cintillo_b64 = ""
    if os.path.exists(cintillo_path):
        with open(cintillo_path, "rb") as f:
            cintillo_b64 = base64.b64encode(f.read()).decode()

    contexto = {
        'persona': persona, 'laboral': laboral,
        'u_n1': u_n1, 'u_n2': u_n2, 'u_n3': u_n3,
        'nivel_nombre': nombre_nivel, 'contactos': contactos,
        'qr_code': qr_b64, 'cintillo': cintillo_b64, 'hoy': date.today(),
    }

    template = get_template('registrov2/fase1/ficha_inicial_trabajadores.html')
    html_content = template.render(contexto)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_content.encode("UTF-8")), result)

    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Ficha_{persona.cedula}.pdf"'
        return response
    
    return HttpResponse("Error en generación de PDF", status=400)


@login_required
@permiso_requerido('generar_ficha_completa')  # 🆕
def generar_ficha_completa_v2(request, trabajador_id):
    """Generar PDF de ficha completa del expediente."""
    trabajador = get_object_or_404(Trabajador, id=trabajador_id)
    persona = trabajador.persona

    u_final = trabajador.unidad_org
    ruta = []
    if u_final:
        actual = u_final
        while actual:
            ruta.insert(0, actual)
            actual = actual.unidad_sup
    nombres_ruta = [u.nombre_unidad for u in ruta] if ruta else ["Sin unidad"]
    nivel_nombre = trabajador.nivel_jerarquico.descripcion if trabajador.nivel_jerarquico else "No definido"

    contactos = PersonaContactoPersonal.objects.filter(persona=persona).select_related('contacto_personal__tipo_contacto')
    emergencias = PersonaContactoEmergencia.objects.filter(persona=persona).select_related('contacto_emergencia')
    vivienda = PersonaVivienda.objects.filter(persona=persona).select_related('vivienda__tipo_vivienda', 'vivienda__condicion_vivienda').first()
    salud = PersonaSalud.objects.filter(persona=persona).select_related('tipo_discapacidad').first()
    patologias = PersonaPatologia.objects.filter(persona=persona, esta_activo=True).select_related('tipo_patologia')
    academicos = FormacionAcademica.objects.filter(persona=persona, esta_activo=True).select_related('nivel_formacion', 'estatus_formacion')
    cursos = FormacionAdicional.objects.filter(persona=persona, esta_activo=True).select_related('tipo_formacion', 'modalidad')
    cargas = PersonaCargaFamiliar.objects.filter(persona=persona, esta_activo=True).select_related('carga_familiar', 'parentesco')

    datos_qr = (
        f"SACAT - EXPEDIENTE COMPLETO\n"
        f"CI: {persona.cedula}\n"
        f"Fecha: {date.today().strftime('%d/%m/%Y')}"
    )
    qr = qrcode.make(datos_qr)
    buf_qr = BytesIO()
    qr.save(buf_qr, format="PNG")
    qr_b64 = base64.b64encode(buf_qr.getvalue()).decode()

    cintillo_path = os.path.join(settings.MEDIA_ROOT, 'cintillo_almccs.png')
    cintillo_b64 = ""
    if os.path.exists(cintillo_path):
        with open(cintillo_path, "rb") as f:
            cintillo_b64 = base64.b64encode(f.read()).decode()

    contexto = {
        'persona': persona, 'laboral': trabajador,
        'ruta_unidades': nombres_ruta, 'nivel_nombre': nivel_nombre,
        'contactos': contactos, 'vivienda': vivienda,
        'salud': salud, 'patologias': patologias,
        'formaciones_academicas': academicos, 'formaciones_adicionales': cursos,
        'cargas_familiares': cargas, 'contactos_emergencia': emergencias,
        'qr_code': qr_b64, 'cintillo': cintillo_b64,
    }

    template = get_template('registrov2/fase2/ficha_completa_trabajador.html')
    html = template.render(contexto)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Ficha_Completa_{persona.cedula}.pdf"'
        return response
    return HttpResponse("Error al generar PDF", status=500)


# =============================================================================
# FASE 2: AUTOGESTIÓN DEL TRABAJADOR (COMPLETACIÓN DE DATOS)
# =============================================================================

@login_required
@permiso_requerido('autogestion_identidad')  # 🆕
def f2_paso1_identidad(request):
    """Autogestión - Paso 1: Identidad."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    persona = trabajador.persona

    if trabajador.fase_actual < 1:
        return redirect('inicio')

    recaudo_ci = Recaudo.objects.filter(
        trabajador=trabajador, 
        tipo_recaudo__descripcion__icontains='IDENTIDAD'
    ).first()

    contexto = {
        'persona': persona, 'trabajador': trabajador,
        'url_cedula': recaudo_ci.ruta_archivo.url if recaudo_ci and recaudo_ci.ruta_archivo else None,
        'hoy': date.today() 
    }
    return render(request, 'registrov2/fase2/f2_paso1_identidad.html', contexto)


@login_required
@permiso_requerido('autogestion_identidad')  # 🆕
def guardar_f2_paso1(request):
    """Guardar cambios de identidad en autogestión."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    persona = trabajador.persona

    archivo = request.FILES.get('archivo_cedula')
    vencimiento_str = request.POST.get('fecha_vencimiento_id', '').strip()
    cambios = False

    if archivo:
        tipo_r = TipoRecaudo.objects.filter(descripcion__icontains='IDENTIDAD').first()
        if not tipo_r:
            return JsonResponse({'success': False, 'error': 'Falta configurar el tipo de recaudo "IDENTIDAD".'})
        Recaudo.objects.update_or_create(
            trabajador=trabajador, tipo_recaudo=tipo_r,
            defaults={'ruta_archivo': archivo, 'actualizado_por': request.user.id}
        )
        cambios = True

    if vencimiento_str:
        try:
            mes, anio = vencimiento_str.split('/')
            fecha_vencimiento = date(int(anio), int(mes), 1)
            if persona.fecha_vencimiento_cedula != fecha_vencimiento:
                persona.fecha_vencimiento_cedula = fecha_vencimiento
                persona.actualizado_por = request.user.id
                persona.save()
                cambios = True
        except (ValueError, IndexError):
            return JsonResponse({'success': False, 'error': 'Formato de vencimiento inválido. Use MM/AAAA.'})

    mensaje = 'Documento de identidad actualizado.' if cambios else 'No se detectaron cambios.'
    return JsonResponse({'success': True, 'mensaje': mensaje})


@login_required
@permiso_requerido('autogestion_contactos')  # 🆕
def f2_paso2_contactos(request):
    """Autogestión - Paso 2: Contactos."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    persona = trabajador.persona

    contactos_p = PersonaContactoPersonal.objects.filter(
        persona=persona
    ).select_related('contacto_personal__tipo_contacto')
    
    contactos_e = PersonaContactoEmergencia.objects.filter(
        persona=persona
    ).select_related('contacto_emergencia')

    contexto = {
        'persona': persona, 'trabajador': trabajador,
        'contactos_guardados': contactos_p,
        'emergencias_guardadas': contactos_e,
        'tipos_contactos': TipoContacto.objects.filter(esta_activo=True),
    }
    return render(request, 'registrov2/fase2/f2_paso2_contactos.html', contexto)


@login_required
@permiso_requerido('autogestion_contactos')  # 🆕
@require_POST
def guardar_f2_paso2(request):
    """Guardar contactos en autogestión."""
    try:
        trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
        persona = trabajador.persona
        user_id = request.user.id

        with transaction.atomic():
            ids_p = request.POST.getlist('contacto_id[]')
            tipos_p = request.POST.getlist('tipo_id[]')
            valores_p = request.POST.getlist('valor[]')
            principales_p = request.POST.getlist('es_principal[]')
            activos_p = request.POST.getlist('contacto_activo[]')

            ids_actuales = [int(i) for i in ids_p if i and i.isdigit()]
            PersonaContactoPersonal.objects.filter(persona=persona).exclude(id__in=ids_actuales).update(esta_activo=False)

            for i, (c_id, t, v, p, a) in enumerate(zip(ids_p, tipos_p, valores_p, principales_p, activos_p)):
                valor_limpio = v.strip().lower()
                if not valor_limpio: continue
                obj_c, _ = ContactoPersonal.objects.update_or_create(
                    valor_contacto=valor_limpio,
                    defaults={'tipo_contacto_id': t, 'actualizado_por': user_id}
                )
                estado = a.lower() == 'true'
                if c_id and c_id.isdigit():
                    PersonaContactoPersonal.objects.filter(id=int(c_id)).update(
                        contacto_personal_id=obj_c.id,
                        es_principal=(p.lower() == 'true'),
                        esta_activo=estado,
                        actualizado_por=user_id
                    )
                else:
                    PersonaContactoPersonal.objects.create(
                        persona=persona, contacto_personal_id=obj_c.id,
                        es_principal=(p.lower() == 'true'),
                        esta_activo=estado, creado_por=user_id
                    )

            ids_e = request.POST.getlist('e_id[]')
            nombres_e = request.POST.getlist('e_nombre[]')
            apellidos_e = request.POST.getlist('e_apellido[]')
            telefonos_e = request.POST.getlist('e_telefono[]')
            activos_e = request.POST.getlist('e_activo[]')

            ids_e_actuales = [int(i) for i in ids_e if i and i.isdigit()]
            PersonaContactoEmergencia.objects.filter(persona=persona).exclude(id__in=ids_e_actuales).update(esta_activo=False)

            for i, (e_id, n, a, t, act) in enumerate(zip(ids_e, nombres_e, apellidos_e, telefonos_e, activos_e)):
                estado_e = act.lower() == 'true'
                obj_e, _ = ContactoEmergencia.objects.update_or_create(
                    primer_nombre=n.strip().upper(),
                    primer_apellido=a.strip().upper(),
                    telefono=t.strip(),
                    defaults={'actualizado_por': user_id}
                )
                if e_id and e_id.isdigit():
                    PersonaContactoEmergencia.objects.filter(id=int(e_id)).update(
                        contacto_emergencia_id=obj_e.id,
                        esta_activo=estado_e,
                        actualizado_por=user_id
                    )
                else:
                    PersonaContactoEmergencia.objects.create(
                        persona=persona, contacto_emergencia_id=obj_e.id,
                        esta_activo=estado_e, creado_por=user_id
                    )

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f"Error en Motor SACAT: {str(e)}"})


@login_required
@permiso_requerido('autogestion_formacion')  # 🆕
def f2_paso3_formacion(request):
    """Autogestión - Paso 3: Formación académica."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    persona = trabajador.persona

    academicos_existentes = FormacionAcademica.objects.filter(
        persona=persona, esta_activo=True
    ).select_related('nivel_formacion', 'estatus_formacion').order_by('-fecha_fin')

    contexto = {
        'academicos_existentes': academicos_existentes,
        'niveles': NivelesFormacion.objects.filter(esta_activo=True).order_by('id'),
        'estatus': EstatusFormacion.objects.filter(esta_activo=True).order_by('id'),
    }
    return render(request, 'registrov2/fase2/f2_paso3_formacion.html', contexto)


@login_required
@permiso_requerido('autogestion_formacion')  # 🆕
@require_POST
def guardar_f2_paso3(request):
    """Guardar formación académica en autogestión."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    persona = trabajador.persona
    user_id = request.user.id

    ids = request.POST.getlist('estudio_id[]')
    niveles = request.POST.getlist('nivel_id[]')
    instituciones = request.POST.getlist('institucion[]')
    especialidades = request.POST.getlist('especialidad[]')
    fechas_inicio = request.POST.getlist('fecha_inicio[]')
    fechas_fin = request.POST.getlist('fecha_fin[]')
    estatus_ids = request.POST.getlist('estatus_id[]')
    activos = request.POST.getlist('estudio_activo[]')

    ids_actuales = [int(i) for i in ids if i and i.isdigit()]

    with transaction.atomic():
        FormacionAcademica.objects.filter(persona=persona).exclude(id__in=ids_actuales).update(esta_activo=False)

        for i in range(len(niveles)):
            if niveles[i] and instituciones[i]:
                estado = activos[i].lower() == 'true' if i < len(activos) else True
                if ids[i] and ids[i].isdigit():
                    FormacionAcademica.objects.filter(id=int(ids[i])).update(
                        nivel_formacion_id=niveles[i],
                        estatus_formacion_id=estatus_ids[i],
                        institucion=instituciones[i].strip().upper(),
                        especialidad=especialidades[i].strip().upper() if especialidades[i] else None,
                        fecha_inicio=fechas_inicio[i] if fechas_inicio[i] else None,
                        fecha_fin=fechas_fin[i] if fechas_fin[i] else None,
                        esta_activo=estado, actualizado_por=user_id
                    )
                else:
                    FormacionAcademica.objects.create(
                        persona=persona, nivel_formacion_id=niveles[i],
                        estatus_formacion_id=estatus_ids[i],
                        institucion=instituciones[i].strip().upper(),
                        especialidad=especialidades[i].strip().upper() if especialidades[i] else None,
                        fecha_inicio=fechas_inicio[i] if fechas_inicio[i] else None,
                        fecha_fin=fechas_fin[i] if fechas_fin[i] else None,
                        esta_activo=estado, creado_por=user_id, actualizado_por=user_id
                    )
    return JsonResponse({'success': True})


@login_required
@permiso_requerido('autogestion_adiestramiento')  # 🆕
def f2_paso4_adiestramiento(request):
    """Autogestión - Paso 4: Adiestramiento."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    persona = trabajador.persona
    cursos = FormacionAdicional.objects.filter(persona=persona, esta_activo=True).select_related('tipo_formacion', 'modalidad')
    contexto = {
        'persona': persona, 'cursos': cursos,
        'tipos_formaciones': TipoFormacion.objects.filter(esta_activo=True),
        'modalidades': Modalidad.objects.filter(esta_activo=True),
    }
    return render(request, 'registrov2/fase2/f2_paso4_adiestramiento.html', contexto)


@login_required
@permiso_requerido('autogestion_adiestramiento')  # 🆕
@require_POST
def guardar_f2_paso4(request):
    """Guardar adiestramiento en autogestión."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    persona = trabajador.persona
    user_id = request.user.id

    ids = request.POST.getlist('curso_id[]')
    tipos = request.POST.getlist('tipo_formacion_id[]')
    nombres = request.POST.getlist('nombre_formacion_ad[]')
    instituciones = request.POST.getlist('institucion_curso[]')
    modalidades = request.POST.getlist('modalidad_id[]')
    horas = request.POST.getlist('duracion_horas[]')
    fechas = request.POST.getlist('fecha_culminacion[]')
    activos = request.POST.getlist('curso_activo[]')

    ids_actuales = [int(i) for i in ids if i and i.isdigit()]

    with transaction.atomic():
        FormacionAdicional.objects.filter(persona=persona).exclude(id__in=ids_actuales).update(esta_activo=False)

        for i in range(len(nombres)):
            if nombres[i] and instituciones[i] and tipos[i] and modalidades[i]:
                estado = activos[i].lower() == 'true' if i < len(activos) else True
                hora_val = horas[i] if i < len(horas) and horas[i] else None
                fecha_val = fechas[i] if i < len(fechas) and fechas[i] else None

                if ids[i] and ids[i].isdigit():
                    FormacionAdicional.objects.filter(id=int(ids[i])).update(
                        tipo_formacion_id=tipos[i], modalidad_id=modalidades[i],
                        nombre_formacion_ad=nombres[i].strip().upper(),
                        institucion=instituciones[i].strip().upper(),
                        duracion_horas=hora_val, fecha_culminacion=fecha_val,
                        esta_activo=estado, actualizado_por=user_id
                    )
                else:
                    FormacionAdicional.objects.create(
                        persona=persona, tipo_formacion_id=tipos[i],
                        modalidad_id=modalidades[i],
                        nombre_formacion_ad=nombres[i].strip().upper(),
                        institucion=instituciones[i].strip().upper(),
                        duracion_horas=hora_val, fecha_culminacion=fecha_val,
                        esta_activo=estado, creado_por=user_id, actualizado_por=user_id
                    )

    return JsonResponse({'success': True})


@login_required
@permiso_requerido('autogestion_salud')  # 🆕
def f2_paso5_salud(request):
    """Autogestión - Paso 5: Salud."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    persona = trabajador.persona
    salud = PersonaSalud.objects.filter(persona=persona).first()
    patologias = PersonaPatologia.objects.filter(persona=persona, esta_activo=True).select_related('tipo_patologia')
    contexto = {
        'persona': persona, 'salud': salud, 'patologias': patologias,
        'tipos_sangre': ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-'],
        'discapacidades': TipoDiscapacidad.objects.filter(esta_activo=True),
        'tipos_patologias': TipoPatologia.objects.filter(esta_activo=True),
    }
    return render(request, 'registrov2/fase2/f2_paso5_salud.html', contexto)


@login_required
@permiso_requerido('autogestion_salud')  # 🆕
@require_POST
def guardar_f2_paso5(request):
    """Guardar salud en autogestión."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    persona = trabajador.persona
    user_id = request.user.id

    tipo_sangre = request.POST.get('tipo_sangre', '').strip()
    tiene_alergias = request.POST.get('tiene_alergias') == 'true'
    tiene_discapacidad = request.POST.get('tiene_discapacidad') == 'true'
    tiene_patologias = request.POST.get('tiene_patologias') == 'true'

    alergias_val = request.POST.get('alergias', '').strip().upper() if tiene_alergias else None
    discapacidad_id = request.POST.get('discapacidad_id') if tiene_discapacidad else None
    nro_conapdis = request.POST.get('nro_conapdis', '').strip() if tiene_discapacidad else None

    with transaction.atomic():
        PersonaSalud.objects.update_or_create(
            persona=persona,
            defaults={
                'tipo_sangre': tipo_sangre or None, 'alergias': alergias_val,
                'tipo_discapacidad_id': discapacidad_id, 'nro_conapdis': nro_conapdis,
                'actualizado_por': user_id
            }
        )

        if tiene_patologias:
            ids_p = request.POST.getlist('patologia_id[]')
            tipos_p = request.POST.getlist('patologia_tipo[]')
            detalles_p = request.POST.getlist('patologia_detalle[]')
            activos_p = request.POST.getlist('patologia_activo[]')

            ids_actuales = [int(i) for i in ids_p if i and i.isdigit()]
            PersonaPatologia.objects.filter(persona=persona).exclude(id__in=ids_actuales).update(esta_activo=False)

            for i in range(len(tipos_p)):
                if tipos_p[i]:
                    estado = activos_p[i].lower() == 'true' if i < len(activos_p) else True
                    detalle = detalles_p[i].strip().upper() if i < len(detalles_p) and detalles_p[i] else None
                    if ids_p[i] and ids_p[i].isdigit():
                        PersonaPatologia.objects.filter(id=int(ids_p[i])).update(
                            tipo_patologia_id=tipos_p[i], descripcion_adicional=detalle,
                            esta_activo=estado, actualizado_por=user_id
                        )
                    else:
                        PersonaPatologia.objects.create(
                            persona=persona, tipo_patologia_id=tipos_p[i],
                            descripcion_adicional=detalle, esta_activo=estado,
                            creado_por=user_id, actualizado_por=user_id
                        )
        else:
            PersonaPatologia.objects.filter(persona=persona).update(esta_activo=False)

    return JsonResponse({'success': True})


@login_required
@permiso_requerido('autogestion_familia')  # 🆕
def f2_paso6_familia(request):
    """Autogestión - Paso 6: Carga familiar."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    persona = trabajador.persona

    familiares = PersonaCargaFamiliar.objects.filter(
        persona=persona
    ).select_related('carga_familiar', 'parentesco', 'carga_familiar__sexo')

    sexo_trabajador = persona.sexo.descripcion.upper() if persona.sexo else ""
    parentescos = Parentesco.objects.filter(esta_activo=True)
    if "FEMENINO" in sexo_trabajador:
        parentescos = parentescos.exclude(descripcion__icontains='ESPOSA')
    elif "MASCULINO" in sexo_trabajador:
        parentescos = parentescos.exclude(descripcion__icontains='ESPOSO')

    contexto = {
        'persona': persona, 'familiares': familiares,
        'parentescos': parentescos.order_by('descripcion'),
        'sexos': Sexo.objects.filter(esta_activo=True),
    }
    return render(request, 'registrov2/fase2/f2_paso6_familia.html', contexto)


@login_required
@permiso_requerido('autogestion_familia')  # 🆕
@require_POST
def guardar_f2_paso6(request):
    """Guardar carga familiar en autogestión."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    persona = trabajador.persona
    user_id = request.user.id

    ids = request.POST.getlist('familiar_id[]')
    cedulas = request.POST.getlist('f_cedula[]')
    nombres1 = request.POST.getlist('f_nombre1[]')
    nombres2 = request.POST.getlist('f_nombre2[]')
    apellidos1 = request.POST.getlist('f_apellido1[]')
    apellidos2 = request.POST.getlist('f_apellido2[]')
    parentescos_ids = request.POST.getlist('f_parentesco_id[]')
    sexos_ids = request.POST.getlist('f_sexo[]')
    fechas_nac = request.POST.getlist('f_nacimiento[]')
    activos = request.POST.getlist('f_activo[]')

    unicos_legales = ['MADRE', 'PADRE', 'ESPOSO', 'ESPOSA', 'CONYUGE']
    ids_actuales = [int(i) for i in ids if i and i.isdigit()]

    try:
        with transaction.atomic():
            PersonaCargaFamiliar.objects.filter(persona=persona).exclude(id__in=ids_actuales).update(esta_activo=False)

            parentescos_enviados = []
            for i in range(len(nombres1)):
                if not nombres1[i] or not apellidos1[i] or not parentescos_ids[i] or not fechas_nac[i] or not sexos_ids[i]:
                    continue

                estado = activos[i].lower() == 'true' if i < len(activos) else True
                cedula_val = cedulas[i].strip() if i < len(cedulas) and cedulas[i] else None

                obj_p = Parentesco.objects.get(id=parentescos_ids[i])
                desc_p = obj_p.descripcion.upper()
                if desc_p in unicos_legales:
                    if desc_p in parentescos_enviados:
                        raise Exception(f"No puede registrar más de un(a) {desc_p}.")
                    parentescos_enviados.append(desc_p)

                hoy = date.today()
                nacimiento = date.fromisoformat(fechas_nac[i])
                edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
                if edad >= 10 and not cedula_val:
                    raise Exception(f"{nombres1[i]} {apellidos1[i]} tiene {edad} años, la cédula es obligatoria.")

                if cedula_val:
                    familiar, _ = CargaFamiliar.objects.update_or_create(
                        cedula=cedula_val,
                        defaults={
                            'primer_nombre': nombres1[i].strip().upper(),
                            'segundo_nombre': nombres2[i].strip().upper() if i < len(nombres2) else None,
                            'primer_apellido': apellidos1[i].strip().upper(),
                            'segundo_apellido': apellidos2[i].strip().upper() if i < len(apellidos2) else None,
                            'fecha_nacimiento': nacimiento, 'sexo_id': sexos_ids[i],
                            'actualizado_por': user_id
                        }
                    )
                else:
                    familiar = CargaFamiliar.objects.create(
                        cedula=None, primer_nombre=nombres1[i].strip().upper(),
                        segundo_nombre=nombres2[i].strip().upper() if i < len(nombres2) else None,
                        primer_apellido=apellidos1[i].strip().upper(),
                        segundo_apellido=apellidos2[i].strip().upper() if i < len(apellidos2) else None,
                        fecha_nacimiento=nacimiento, sexo_id=sexos_ids[i],
                        creado_por=user_id
                    )

                if ids[i] and ids[i].isdigit():
                    PersonaCargaFamiliar.objects.filter(id=int(ids[i])).update(
                        carga_familiar_id=familiar.id, parentesco_id=parentescos_ids[i],
                        esta_activo=estado, actualizado_por=user_id
                    )
                else:
                    PersonaCargaFamiliar.objects.create(
                        persona=persona, carga_familiar_id=familiar.id,
                        parentesco_id=parentescos_ids[i], esta_activo=estado,
                        creado_por=user_id
                    )

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permiso_requerido('autogestion_laboral')  # 🆕
def f2_paso7_laboral(request):
    """Autogestión - Paso 7: Resumen laboral (solo lectura)."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    persona = trabajador.persona

    u_final = trabajador.unidad_org
    ruta = []
    if u_final:
        actual = u_final
        while actual:
            ruta.insert(0, actual)
            actual = actual.unidad_sup
    nombres_ruta = [u.nombre_unidad for u in ruta] if ruta else ["Sin unidad"]
    nivel_nombre = trabajador.nivel_jerarquico.descripcion if trabajador.nivel_jerarquico else "No definido"

    contexto = {
        'persona': persona, 'trabajador': trabajador, 'laboral': trabajador,
        'nivel_nombre': nivel_nombre, 'ruta_unidades': nombres_ruta,
    }
    return render(request, 'registrov2/fase2/f2_paso7_laboral.html', contexto)


@login_required
@permiso_requerido('autogestion_comprobante')  # 🆕
def f2_comprobante(request):
    """Autogestión - Paso 8: Comprobante final."""
    trabajador = get_object_or_404(Trabajador, persona__cedula=request.user.nombre_usuario)
    persona = trabajador.persona

    u_final = trabajador.unidad_org
    ruta = []
    if u_final:
        actual = u_final
        while actual:
            ruta.insert(0, actual)
            actual = actual.unidad_sup
    nombres_ruta = [u.nombre_unidad for u in ruta] if ruta else ["Sin unidad"]

    contactos = PersonaContactoPersonal.objects.filter(persona=persona).select_related('contacto_personal__tipo_contacto')
    emergencia = PersonaContactoEmergencia.objects.filter(persona=persona).select_related('contacto_emergencia').first()
    vivienda = PersonaVivienda.objects.filter(persona=persona).select_related('vivienda__tipo_vivienda', 'vivienda__condicion_vivienda').first()
    salud = PersonaSalud.objects.filter(persona=persona).select_related('tipo_discapacidad').first()
    patologias = PersonaPatologia.objects.filter(persona=persona, esta_activo=True).select_related('tipo_patologia')
    academicos = FormacionAcademica.objects.filter(persona=persona, esta_activo=True).select_related('nivel_formacion', 'estatus_formacion')
    cursos = FormacionAdicional.objects.filter(persona=persona, esta_activo=True).select_related('tipo_formacion', 'modalidad')
    cargas = PersonaCargaFamiliar.objects.filter(persona=persona, esta_activo=True).select_related('carga_familiar', 'parentesco')
    emergencias = PersonaContactoEmergencia.objects.filter(persona=persona).select_related('contacto_emergencia')

    contexto = {
        'persona': persona, 'laboral': trabajador,
        'ruta_unidades': nombres_ruta,
        'nivel_nombre': trabajador.nivel_jerarquico.descripcion if trabajador.nivel_jerarquico else "No definido",
        'contactos': contactos, 'vivienda': vivienda,
        'salud': salud, 'patologias': patologias,
        'formaciones_academicas': academicos, 'formaciones_adicionales': cursos,
        'cargas_familiares': cargas, 'contactos_emergencia': emergencias,
        'trabajador_id': trabajador.id,
    }
    return render(request, 'registrov2/fase2/f2_comprobante.html', contexto)

# =============================================================================
# PERFIL PROPIO DEL TRABAJADOR (AUTOCONSULTA)
# =============================================================================

@login_required
@permiso_requerido('ver_mi_perfil')
def mi_perfil(request):
    """
    Muestra el perfil del trabajador logueado.
    Reutiliza completamente la vista perfil_trabajador.
    """
    trabajador = get_object_or_404(
        Trabajador.objects.select_related('persona'),
        persona__cedula=request.user.nombre_usuario
    )
    
    # Reutiliza la vista existente
    return perfil_trabajador(request, trabajador.id)