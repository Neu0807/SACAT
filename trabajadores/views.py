from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date
from django.core.mail import send_mail
from django.conf import settings
import json, secrets, string
from seguridad.models import Rol, Usuario  # Tus modelos personalizados
from seguridad.views import generar_clave_robusta
import os
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
import qrcode
import base64


# --- MODELOS DE CONFIGURACIÓN ---
from configuracion.models import (
    TipoDocIdentificacion, Sexo, EstadoCivil, 
    Estado, Municipio, Parroquia, Direccion, TipoContacto,
    TiposVivienda, CondicionesVivienda, CentroVotacion,
    TipoDiscapacidad, TipoPatologia, NivelesFormacion, 
    EstatusFormacion, UnidadesOrganizativas, CargosGenerico, 
    CargosEstructural, Parentesco, Sede, TipoFormacion, Modalidad
)

# --- MODELOS DE TRABAJADORES ---
from .models import (
    Persona, PersonaDireccion, Vivienda, PersonaVivienda,
    ContactoPersonal, PersonaContactoPersonal, 
    ContactoEmergencia, PersonaContactoEmergencia,
    FormacionAcademica, FormacionAdicional,
    DatosElectorales, PersonaSalud, PersonaPatologia,
    CargaFamiliar, PersonaCargaFamiliar, Trabajador
)

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
    if 'registro_persona_id' not in request.session: return redirect('registro_paso1')
    contexto = { 'tipos_contactos': TipoContacto.objects.filter(esta_activo=True).order_by('descripcion') }
    return render(request, 'registro/contactos.html', contexto)

@login_required
@require_POST
def guardar_paso3(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        indice_principal = int(request.POST.get('indice_principal', 0))

        with transaction.atomic():
            tipos_p = request.POST.getlist('tipo_contacto[]')
            valores_p = request.POST.getlist('valor_contacto[]')
            for i, (t, v) in enumerate(zip(tipos_p, valores_p)):
                if t and v:
                    c_personal = ContactoPersonal.objects.create(
                        tipo_contacto_id=t, valor_contacto=v.strip().lower(), creado_por=user_id
                    )
                    PersonaContactoPersonal.objects.create(
                        persona_id=persona_id, contacto_personal_id=c_personal.id,
                        es_principal=(i == indice_principal), creado_por=user_id
                    )

            nombres_e = request.POST.getlist('e_nombre[]')
            apellidos_e = request.POST.getlist('e_apellido[]')
            telefonos_e = request.POST.getlist('e_telefono[]')
            for n, a, tel in zip(nombres_e, apellidos_e, telefonos_e):
                if n and tel:
                    c_emergencia = ContactoEmergencia.objects.create(
                        primer_nombre=n.strip().upper(), primer_apellido=a.strip().upper(),
                        telefono=tel.strip(), creado_por=user_id
                    )
                    PersonaContactoEmergencia.objects.create(
                        persona_id=persona_id, contacto_emergencia_id=c_emergencia.id, creado_por=user_id
                    )

        return JsonResponse({'success': True, 'next_url': reverse('registro_paso4')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# --- PASO 4: FORMACIÓN ACADÉMICA ---
@login_required
def registro_paso4(request):
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    contexto = {
        'niveles': NivelesFormacion.objects.filter(esta_activo=True).order_by('id'),
        'estatus': EstatusFormacion.objects.filter(esta_activo=True).order_by('id'),
    }
    return render(request, 'registro/formacion.html', contexto)

@login_required
@require_POST
def guardar_paso4(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
        # Atrapamos las listas del formulario
        niveles = request.POST.getlist('nivel_id[]')
        instituciones = request.POST.getlist('institucion[]')
        estatus_ids = request.POST.getlist('estatus_id[]')
        especialidades = request.POST.getlist('especialidad[]')
        fechas_inicio = request.POST.getlist('fecha_inicio[]') # No olvides capturar el inicio
        fechas_fin = request.POST.getlist('fecha_fin[]')

        # 🌟 LA DECISIÓN DEL SALTO 🌟
        # Leemos el valor que viene del switch del HTML
        posee_formacion_adicional = request.POST.get('ir_a_cursos') == 'true'

        with transaction.atomic():
            for i in range(len(niveles)):
                if niveles[i] and instituciones[i]:
                    FormacionAcademica.objects.create(
                        persona_id=persona_id, 
                        nivel_formacion_id=niveles[i],
                        estatus_formacion_id=estatus_ids[i],
                        institucion=instituciones[i].strip().upper(),
                        especialidad=especialidades[i].strip().upper() if especialidades[i] else None,
                        fecha_inicio=fechas_inicio[i] if fechas_inicio[i] else None,
                        fecha_fin=fechas_fin[i] if fechas_fin[i] else None,
                        creado_por=user_id,
                        actualizado_por=user_id
                    )

        # 🚀 AQUÍ ESTÁ EL TRUCO:
        # Si tiene cursos -> Paso 5 (adiestramiento)
        # Si NO tiene cursos -> Paso 6 (salud)
        if posee_formacion_adicional:
            url_destino = reverse('registro_paso5')
        else:
            url_destino = reverse('registro_paso6')

        return JsonResponse({'success': True, 'next_url': url_destino})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# --- PASO 5: ADIESTRAMIENTO ---
@login_required
def registro_paso5(request):
    if 'registro_persona_id' not in request.session: 
        return redirect('registro_paso1')
    
    # 🌟 Aquí mandamos los catálogos nuevos al HTML 🌟
    contexto = {
        'tipos_formaciones': TipoFormacion.objects.filter(esta_activo=True).order_by('id'),
        'modalidades': Modalidad.objects.filter(esta_activo=True).order_by('id'),
    }
    return render(request, 'registro/adiestramiento.html', contexto)

@login_required
@require_POST
def guardar_paso5(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
        # 🌟 Atajamos TODAS las listas que vienen del HTML (incluyendo las nuevas) 🌟
        tipos = request.POST.getlist('tipo_formacion_id[]')
        nombres = request.POST.getlist('nombre_formacion_ad[]')
        instituciones = request.POST.getlist('institucion[]')
        modalidades = request.POST.getlist('modalidad_id[]')
        horas = request.POST.getlist('duracion_horas[]')
        fechas = request.POST.getlist('fecha_culminacion[]')

        with transaction.atomic():
            for i in range(len(nombres)):
                # Validamos que vengan los datos obligatorios
                if nombres[i] and instituciones[i] and tipos[i] and modalidades[i]:
                    FormacionAdicional.objects.create(
                        persona_id=persona_id, 
                        tipo_formacion_id=tipos[i],         # NUEVO
                        modalidad_id=modalidades[i],        # NUEVO
                        nombre_formacion_ad=nombres[i].strip().upper(),
                        institucion=instituciones[i].strip().upper(),
                        duracion_horas=horas[i] if horas[i] else None,
                        fecha_culminacion=fechas[i] if fechas[i] else None,
                        creado_por=user_id, 
                        actualizado_por=user_id
                    )

        return JsonResponse({'success': True, 'next_url': reverse('registro_paso6')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# --- PASO 6: SALUD Y DISCAPACIDAD ---
@login_required
def registro_paso6(request):
    if 'registro_persona_id' not in request.session: return redirect('registro_paso1')
    contexto = {
        'discapacidades': TipoDiscapacidad.objects.filter(esta_activo=True).order_by('descripcion'),
        'patologias': TipoPatologia.objects.filter(esta_activo=True).order_by('descripcion'),
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
    
    # 🌟 OBTENEMOS LOS DATOS DEL TRABAJADOR PARA FILTRAR
    persona_id = request.session.get('registro_persona_id')
    persona = get_object_or_404(Persona, id=persona_id)
    sexo_trabajador = persona.sexo.descripcion.upper()

    # 🌟 FILTRO LEGAL DE PARENTESCOS SEGÚN SEXO
    parentescos = Parentesco.objects.filter(esta_activo=True)
    
    if "FEMENINO" in sexo_trabajador:
        parentescos = parentescos.exclude(descripcion__icontains='ESPOSA')
    elif "MASCULINO" in sexo_trabajador:
        parentescos = parentescos.exclude(descripcion__icontains='ESPOSO')

    contexto = {
        'parentescos': parentescos.order_by('descripcion'),
        'sexos': Sexo.objects.filter(esta_activo=True).order_by('descripcion'),
    }
    return render(request, 'registro/carga_familiar.html', contexto)

@login_required
@require_POST
def guardar_paso7(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        
        # Atrapamos las listas del POST
        nombres = request.POST.getlist('f_nombres[]') # Ajustado a tu HTML nombres
        apellidos = request.POST.getlist('f_apellidos[]')
        parentescos_ids = request.POST.getlist('f_parentesco_id[]')
        cedulas = request.POST.getlist('f_cedula[]')
        fechas_nac = request.POST.getlist('f_nacimiento[]')
        sexos_ids = request.POST.getlist('f_sexo[]') # Asegúrate de añadir el campo sexo en el HTML si no estaba

        # 🌟 VALIDACIÓN DE UNICIDAD EN SERVIDOR
        # Parentescos que no se pueden repetir legalmente
        unicos_legales = ['MADRE', 'PADRE', 'ESPOSO', 'ESPOSA', 'CONYUGE']
        parentescos_enviados = []

        with transaction.atomic():
            for i in range(len(nombres)):
                if nombres[i] and parentescos_ids[i]:
                    # Verificar si el parentesco es único
                    obj_p = Parentesco.objects.get(id=parentescos_ids[i])
                    desc_p = obj_p.descripcion.upper()
                    
                    if desc_p in unicos_legales:
                        if desc_p in parentescos_enviados:
                            raise Exception(f"No puede registrar más de un(a) {desc_p}.")
                        parentescos_enviados.append(desc_p)

                    # 1. Crear la Carga Familiar
                    familiar = CargaFamiliar.objects.create(
                        cedula=cedulas[i].strip() if cedulas[i] else None,
                        primer_nombre=nombres[i].strip().upper(),
                        primer_apellido=apellidos[i].strip().upper(),
                        fecha_nacimiento=fechas_nac[i],
                        sexo_id=sexos_ids[i] if i < len(sexos_ids) else None, # Validación de índice
                        creado_por=user_id
                    )
                    
                    # 2. Crear la relación con el trabajador
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
    if 'registro_persona_id' not in request.session: return redirect('registro_paso1')
    contexto = {
        'unidades': UnidadesOrganizativas.objects.filter(esta_activo=True).order_by('nombre_unidad'),
        'cargos_gen': CargosGenerico.objects.filter(esta_activo=True).order_by('nombre_cargo'),
        'cargos_est': CargosEstructural.objects.filter(esta_activo=True).order_by('nombre_cargo_estruct'),
        'sedes': Sede.objects.filter(esta_activo=True).order_by('nombre_sede'),
    }
    return render(request, 'registro/datos_laborales.html', contexto)

@login_required
@require_POST
def guardar_paso8(request):
    try:
        persona_id = request.session.get('registro_persona_id')
        user_id = request.user.id
        with transaction.atomic():
            Trabajador.objects.create(
                persona_id=persona_id,
                unidad_org_id=request.POST.get('unidad_id'),
                cargo_generico_id=request.POST.get('cargo_gen_id'),
                cargo_estructural_id=request.POST.get('cargo_est_id'),
                codigo_nomina=request.POST.get('codigo_nomina').strip().upper(),
                fecha_ingreso_inst=request.POST.get('fecha_ingreso'),
                creado_por=user_id, actualizado_por=user_id
            )
        return JsonResponse({'success': True, 'next_url': reverse('registro_paso9')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

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
    
    # 1. GENERACIÓN DEL CÓDIGO QR "CRIMINAL"
    # El QR contiene la cédula, el validador y un enlace (opcional)
    # Puedes usar reverse('listar_usuarios') o una vista de perfil si la tienes
    link_verificacion = request.build_absolute_uri('/') 
    datos_qr = f"SACAT-ID: {persona.cedula}\nTrabajador: {persona.primer_nombre} {persona.primer_apellido}\nValidado por: {request.user.nombre_usuario}\nFecha: {date.today()}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(datos_qr)
    qr.make(fit=True)
    
    img_qr = qr.make_image(fill_color="black", back_color="white")
    buffer_qr = BytesIO()
    img_qr.save(buffer_qr, format="PNG")
    qr_base64 = base64.b64encode(buffer_qr.getvalue()).decode()

    # 2. RECOLECCIÓN MAESTRA DE DATOS (Los 8 Pasos)
    contexto = {
        'persona': persona,
        'qr_code': qr_base64, # <--- Enviamos el QR en base64
        'direccion': PersonaDireccion.objects.filter(persona=persona, es_principal=True).first(),
        'vivienda': PersonaVivienda.objects.filter(persona=persona).first(),
        'electoral': DatosElectorales.objects.filter(persona=persona).first(),
        'contactos': PersonaContactoPersonal.objects.filter(persona=persona),
        'correo': PersonaContactoPersonal.objects.filter(
            persona=persona, 
            contacto_personal__tipo_contacto__descripcion__icontains='CORREO'
        ).select_related('contacto_personal').first(),
        'emergencia': PersonaContactoEmergencia.objects.filter(persona=persona).select_related('contacto_emergencia').first(),
        'academicos': FormacionAcademica.objects.filter(persona=persona).order_by('-fecha_fin'),
        'cursos': FormacionAdicional.objects.filter(persona=persona).order_by('-fecha_culminacion'),
        'salud': PersonaSalud.objects.filter(persona=persona).first(),
        'patologias': PersonaPatologia.objects.filter(persona=persona).select_related('tipo_patologia'),
        'familia': PersonaCargaFamiliar.objects.filter(persona=persona).select_related('carga_familiar', 'parentesco'),
        'laboral': Trabajador.objects.filter(persona=persona).select_related('unidad_org', 'cargo_estructural').first(),
        'hoy': date.today(),
    }

    # 3. RENDERIZADO Y GENERACIÓN DEL PDF
    template = get_template('registro/ficha_trabajador_maestra.html')
    html = template.render(contexto)
    result = BytesIO()

    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Ficha_{persona.cedula}.pdf"'
        return response
    
    return HttpResponse("Error al generar el reporte", status=400)