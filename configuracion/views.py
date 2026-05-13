import csv
import io
import openpyxl
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

# 🆕 Importamos el decorador personalizado de permisos
from seguridad.decorators import permiso_requerido

from .models import (
    Estado, Municipio, Parroquia, TipoDocIdentificacion, 
    Sexo, EstadoCivil, TipoContacto, CentroVotacion,
    ItemsDotaciones,
    TallasDotaciones,
)


# =============================================================================
# FUNCIÓN AUXILIAR PARA IMPORTACIÓN
# =============================================================================

def obtener_datos_archivo(archivo):
    """Función auxiliar para normalizar la lectura de Excel y CSV"""
    nombre_archivo = archivo.name.lower()
    if nombre_archivo.endswith(('.xlsx', '.xls')):
        try:
            wb = openpyxl.load_workbook(archivo, data_only=True)
            hoja = wb.active
            return list(hoja.iter_rows(min_row=2, values_only=True))
        except Exception:
            return None
    elif nombre_archivo.endswith('.csv'):
        try:
            contenido = archivo.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            archivo.seek(0)
            contenido = archivo.read().decode('latin-1')
        
        lector = csv.reader(io.StringIO(contenido))
        next(lector, None)
        return list(lector)
    return None


# =============================================================================
# SUBMÓDULO: UBICACIÓN GEOGRÁFICA
# =============================================================================

@login_required
@permiso_requerido('ver_ubicacion')  # 🆕
def configuracion_ubicacion(request):
    """Menú principal de ubicación geográfica."""
    return render(request, 'ubicacion/ubicacion_menu.html')


# --- Estados ---

@login_required
@permiso_requerido('ver_estados')  # 🆕
def listar_estados(request):
    """Listar todos los estados."""
    estados = Estado.objects.all().order_by('nombre_estado')
    return render(request, 'ubicacion/listar_estados.html', {'estados': estados})


@login_required
@permiso_requerido('inhabilitar_estado')  # 🆕
@require_POST
def toggle_estado(request, estado_id):
    """Activar o inhabilitar un estado."""
    try:
        estado = Estado.objects.get(id=estado_id)
        data = json.loads(request.body)
        nuevo_estatus = data.get('esta_activo', True)
        
        estado.esta_activo = nuevo_estatus
        estado.actualizado_por = request.user.id
        estado.save()
        
        estado_texto = "habilitado" if nuevo_estatus else "inhabilitado"
        return JsonResponse({'success': True, 'mensaje': f'El estado ha sido {estado_texto}.'})
        
    except Estado.DoesNotExist:
        return JsonResponse({'success': False, 'mensaje': 'El estado no existe.'})
    except Exception as e:
        return JsonResponse({'success': False, 'mensaje': f'Error: {str(e)}'})


@login_required
@permiso_requerido('importar_estados')  # 🆕
def importar_estados(request):
    """Importar estados desde archivo Excel/CSV."""
    if request.method == 'POST' and request.FILES.get('archivo'):
        datos = obtener_datos_archivo(request.FILES['archivo'])
        if datos is None:
            return JsonResponse({'success': False, 'mensaje': 'Formato no soportado.'})

        contador = 0
        try:
            for fila in datos:
                if fila and len(fila) >= 1 and fila[0]:
                    nombre = str(fila[0]).strip().upper()
                    Estado.objects.get_or_create(
                        nombre_estado=nombre,
                        defaults={
                            'creado_por': request.user.id,
                            'actualizado_por': request.user.id,
                            'esta_activo': True
                        }
                    )
                    contador += 1
            return JsonResponse({'success': True, 'mensaje': f'¡Fino! Se procesaron {contador} estados.'})
        except Exception as e:
            return JsonResponse({'success': False, 'mensaje': f'Error: {str(e)}'})
    return JsonResponse({'success': False, 'mensaje': 'Solicitud inválida.'})


# --- Municipios ---

@login_required
@permiso_requerido('ver_municipios')  # 🆕
def listar_municipios(request):
    """Listar todos los municipios."""
    municipios = Municipio.objects.select_related('estado').all().order_by('estado__nombre_estado', 'nombre_municipio')
    return render(request, 'ubicacion/listar_municipios.html', {'municipios': municipios})


@login_required
@permiso_requerido('inhabilitar_municipio')  # 🆕
@require_POST
def toggle_municipio(request, municipio_id):
    """Activar o inhabilitar un municipio."""
    try:
        municipio = Municipio.objects.get(id=municipio_id)
        data = json.loads(request.body)
        nuevo_estatus = data.get('esta_activo', True)
        
        municipio.esta_activo = nuevo_estatus
        municipio.actualizado_por = request.user.id
        municipio.save()
        
        estado_texto = "habilitado" if nuevo_estatus else "inhabilitado"
        return JsonResponse({'success': True, 'mensaje': f'El municipio ha sido {estado_texto}.'})
        
    except Municipio.DoesNotExist:
        return JsonResponse({'success': False, 'mensaje': 'El municipio no existe.'})
    except Exception as e:
        return JsonResponse({'success': False, 'mensaje': f'Error: {str(e)}'})


@login_required
@permiso_requerido('importar_municipios')  # 🆕
def importar_municipios(request):
    """Importar municipios desde archivo Excel/CSV."""
    if request.method == 'POST' and request.FILES.get('archivo'):
        datos = obtener_datos_archivo(request.FILES['archivo'])
        if datos is None: 
            return JsonResponse({'success': False, 'mensaje': 'Formato no soportado.'})

        contador = 0
        errores = 0
        try:
            for fila in datos:
                if fila and len(fila) >= 2:
                    nom_est = str(fila[0]).strip()
                    nom_mun = str(fila[1]).strip().upper()
                    
                    obj_estado = Estado.objects.filter(nombre_estado__iexact=nom_est).first()
                    if obj_estado:
                        Municipio.objects.get_or_create(
                            nombre_municipio=nom_mun,
                            estado=obj_estado,
                            defaults={
                                'creado_por': request.user.id,
                                'actualizado_por': request.user.id
                            }
                        )
                        contador += 1
                    else:
                        errores += 1
            
            msj = f'Se importaron {contador} municipios.'
            if errores > 0:
                msj += f' No se encontraron {errores} estados referenciados.'
                
            return JsonResponse({'success': True, 'mensaje': msj})
        except Exception as e:
            return JsonResponse({'success': False, 'mensaje': f'Error: {str(e)}'})
    return JsonResponse({'success': False, 'mensaje': 'Error en la petición.'})


# --- Parroquias ---

@login_required
@permiso_requerido('ver_parroquias')  # 🆕
def listar_parroquias(request):
    """Listar todas las parroquias."""
    parroquias = Parroquia.objects.select_related('municipio__estado').all().order_by('municipio__estado__nombre_estado', 'nombre_parroquia')
    return render(request, 'ubicacion/listar_parroquias.html', {'parroquias': parroquias})


@login_required
@permiso_requerido('inhabilitar_parroquia')  # 🆕
@require_POST
def toggle_parroquia(request, parroquia_id):
    """Activar o inhabilitar una parroquia."""
    try:
        parroquia = Parroquia.objects.get(id=parroquia_id)
        data = json.loads(request.body)
        nuevo_estatus = data.get('esta_activo', True)
        
        parroquia.esta_activo = nuevo_estatus
        parroquia.actualizado_por = request.user.id
        parroquia.save()
        
        estado_texto = "habilitado" if nuevo_estatus else "inhabilitado"
        return JsonResponse({'success': True, 'mensaje': f'La parroquia ha sido {estado_texto}.'})
        
    except Parroquia.DoesNotExist:
        return JsonResponse({'success': False, 'mensaje': 'La parroquia no existe.'})
    except Exception as e:
        return JsonResponse({'success': False, 'mensaje': f'Error: {str(e)}'})


@login_required
@permiso_requerido('importar_parroquias')  # 🆕
def importar_parroquias(request):
    """Importar parroquias desde archivo Excel/CSV."""
    if request.method == 'POST' and request.FILES.get('archivo'):
        datos = obtener_datos_archivo(request.FILES['archivo'])
        if datos is None: 
            return JsonResponse({'success': False, 'mensaje': 'Formato no soportado.'})

        contador = 0
        errores = 0
        try:
            for fila in datos:
                if fila and len(fila) >= 3:
                    nom_est = str(fila[0]).strip()
                    nom_mun = str(fila[1]).strip()
                    nom_par = str(fila[2]).strip().upper()
                    
                    obj_mun = Municipio.objects.filter(
                        nombre_municipio__iexact=nom_mun,
                        estado__nombre_estado__iexact=nom_est
                    ).first()
                    
                    if obj_mun:
                        Parroquia.objects.get_or_create(
                            nombre_parroquia=nom_par,
                            municipio=obj_mun,
                            defaults={'creado_por': request.user.id}
                        )
                        contador += 1
                    else:
                        errores += 1
                        
            msj = f'¡Fino! Se importaron {contador} parroquias exitosamente.'
            if errores > 0:
                msj += f' Hubo {errores} filas ignoradas por no coincidir el Municipio/Estado.'
                
            return JsonResponse({'success': True, 'mensaje': msj})
        except Exception as e:
            return JsonResponse({'success': False, 'mensaje': f'Error en procesamiento: {str(e)}'})
    return JsonResponse({'success': False, 'mensaje': 'Archivo no recibido.'})


# =============================================================================
# SUBMÓDULO: IDENTIDAD
# =============================================================================

@login_required
@permiso_requerido('ver_identidad')  # 🆕
def configuracion_identidad(request):
    """Menú principal de identidad."""
    return render(request, 'configuracion/identidad_menu.html')


# --- Tipos de Documentos ---

@login_required
@permiso_requerido('ver_tipos_documentos')  # 🆕
def listar_tipos_docs(request):
    """Listar tipos de documentos de identidad."""
    documentos = TipoDocIdentificacion.objects.all().order_by('id')
    return render(request, 'configuracion/identidad/listar_tipos_docs.html', {'documentos': documentos})


@login_required
@permiso_requerido('crear_tipo_documento')  # 🆕
@require_POST
def crear_tipo_documento(request):
    """Registrar un nuevo tipo de documento."""
    try:
        sigla = request.POST.get('sigla', '').strip().upper()
        descripcion = request.POST.get('descripcion', '').strip()
        ente_emisor = request.POST.get('ente_emisor', '').strip()
        aplica_a = request.POST.get('aplica_a', '').strip()

        if not sigla or not descripcion:
            return JsonResponse({'success': False, 'error': 'Sigla y Descripción son obligatorios.'})

        if TipoDocIdentificacion.objects.filter(sigla=sigla).exists():
            return JsonResponse({'success': False, 'error': f'La sigla "{sigla}" ya está registrada.'})

        TipoDocIdentificacion.objects.create(
            sigla=sigla,
            descripcion=descripcion,
            ente_emisor=ente_emisor if ente_emisor else None,
            aplica_a=aplica_a,
            esta_activo=True,
            creado_por=request.user.id,
            actualizado_por=request.user.id
        )

        return JsonResponse({
            'success': True, 
            'message': f'Documento "{sigla}" registrado con éxito.'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permiso_requerido('editar_tipo_documento')  # 🆕
@require_POST
def editar_tipo_documento(request, doc_id):
    """Editar un tipo de documento existente."""
    try:
        documento = TipoDocIdentificacion.objects.get(id=doc_id)
        documento.sigla = request.POST.get('sigla', '').strip().upper()
        documento.descripcion = request.POST.get('descripcion', '').strip()
        documento.ente_emisor = request.POST.get('ente_emisor', '').strip()
        documento.aplica_a = request.POST.get('aplica_a', '').strip()
        
        documento.actualizado_por = request.user.id
        documento.save()
        
        return JsonResponse({'success': True, 'message': 'Documento actualizado con éxito.'})
    except TipoDocIdentificacion.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'El documento no existe.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permiso_requerido('inhabilitar_tipo_documento')  # 🆕
@require_POST
def toggle_tipo_doc(request, doc_id):
    """Activar o inhabilitar un tipo de documento."""
    try:
        documento = TipoDocIdentificacion.objects.get(id=doc_id)
        data = json.loads(request.body)
        nuevo_estatus = data.get('esta_activo', True)
        
        documento.esta_activo = nuevo_estatus
        documento.actualizado_por = request.user.id
        documento.save()
        
        estado_texto = "habilitado" if nuevo_estatus else "inhabilitado"
        return JsonResponse({'success': True, 'mensaje': f'El documento ha sido {estado_texto}.'})
        
    except TipoDocIdentificacion.DoesNotExist:
        return JsonResponse({'success': False, 'mensaje': 'El tipo de documento no existe.'})
    except Exception as e:
        return JsonResponse({'success': False, 'mensaje': f'Error: {str(e)}'})


# --- Sexos ---

@login_required
@permiso_requerido('ver_sexos')  # 🆕
def listar_sexos(request):
    """Listar catálogo de sexos."""
    sexos = Sexo.objects.all().order_by('id')
    return render(request, 'configuracion/identidad/listar_sexos.html', {'sexos': sexos})


@login_required
@permiso_requerido('inhabilitar_sexo')  # 🆕
@require_POST
def toggle_sexo(request, sexo_id):
    """Activar o inhabilitar un sexo."""
    sexo = get_object_or_404(Sexo, id=sexo_id)
    data = json.loads(request.body)
    sexo.esta_activo = data.get('esta_activo', not sexo.esta_activo)
    sexo.actualizado_por = request.user.id
    sexo.save()
    estado = "habilitado" if sexo.esta_activo else "inhabilitado"
    return JsonResponse({'success': True, 'mensaje': f'Sexo {estado}.'})


# --- Estados Civiles ---

@login_required
@permiso_requerido('ver_estados_civiles')  # 🆕
def listar_estados_civiles(request):
    """Listar catálogo de estados civiles."""
    estados_civiles = EstadoCivil.objects.all().order_by('id')
    return render(request, 'configuracion/identidad/listar_estados_civiles.html', {'estados_civiles': estados_civiles})


@login_required
@permiso_requerido('inhabilitar_estado_civil')  # 🆕
@require_POST
def toggle_estado_civil(request, estadocivil_id):
    """Activar o inhabilitar un estado civil."""
    ec = get_object_or_404(EstadoCivil, id=estadocivil_id)
    data = json.loads(request.body)
    ec.esta_activo = data.get('esta_activo', not ec.esta_activo)
    ec.actualizado_por = request.user.id
    ec.save()
    estado = "habilitado" if ec.esta_activo else "inhabilitado"
    return JsonResponse({'success': True, 'mensaje': f'Estado civil {estado}.'})


# --- Tipos de Contactos ---

@login_required
@permiso_requerido('ver_tipos_contactos')  # 🆕
def listar_tipos_contactos(request):
    """Listar catálogo de tipos de contactos."""
    contactos = TipoContacto.objects.all().order_by('id')
    return render(request, 'configuracion/identidad/listar_tipos_contactos.html', {'contactos': contactos})


# =============================================================================
# SUBMÓDULO: INSTITUCIÓN / ESTRUCTURA / LABORAL / ENTORNO
# =============================================================================

@login_required
@permiso_requerido('ver_institucion')  # 🆕
def configuracion_institucion(request):
    """Menú de configuración institucional."""
    return render(request, 'configuracion/institucion_menu.html')


@login_required
@permiso_requerido('ver_estructura')  # 🆕
def configuracion_estructura(request):
    """Menú de estructura organizativa."""
    return render(request, 'configuracion/estructura_menu.html')


@login_required
@permiso_requerido('ver_laboral')  # 🆕
def configuracion_laboral(request):
    """Menú de configuración laboral."""
    return render(request, 'configuracion/laboral_menu.html')


@login_required
@permiso_requerido('ver_entorno')  # 🆕
def configuracion_entorno(request):
    """Menú de configuración del entorno."""
    return render(request, 'configuracion/entorno_menu.html')


# =============================================================================
# SUBMÓDULO: DOTACIÓN
# =============================================================================

@login_required
@permiso_requerido('ver_dotacion')  # 🆕
def configuracion_dotacion(request):
    """Menú principal de dotación."""
    return render(request, 'dotacion/dotacion_menu.html')


# --- Ítems de Dotación ---

@login_required
@permiso_requerido('ver_items_dotacion')  # 🆕
def listar_items_dotaciones(request):
    """Listar ítems de dotación."""
    items = ItemsDotaciones.objects.all().order_by('id')
    return render(request, 'dotacion/listar_items_dotaciones.html', {'items': items})


@login_required
@permiso_requerido('inhabilitar_item_dotacion')  # 🆕
@require_POST
def toggle_item_dotacion(request, item_id):
    """Activar o inhabilitar un ítem de dotación."""
    item = get_object_or_404(ItemsDotaciones, id=item_id)
    item.esta_activo = not item.esta_activo
    item.actualizado_por = request.user.id
    item.save()
    estado = "habilitado" if item.esta_activo else "inhabilitado"
    return JsonResponse({'success': True, 'mensaje': f'Ítem de dotación {estado}.'})


# --- Tallas de Dotación ---

@login_required
@permiso_requerido('ver_tallas_dotacion')  # 🆕
def listar_tallas_dotaciones(request):
    """Listar tallas de dotación."""
    tallas = TallasDotaciones.objects.select_related('item_dotacion').all().order_by('id')
    return render(request, 'dotacion/listar_tallas_dotaciones.html', {'tallas': tallas})


@login_required
@permiso_requerido('inhabilitar_talla_dotacion')  # 🆕
@require_POST
def toggle_talla_dotacion(request, talla_id):
    """Activar o inhabilitar una talla de dotación."""
    talla = get_object_or_404(TallasDotaciones, id=talla_id)
    talla.esta_activo = not talla.esta_activo
    talla.actualizado_por = request.user.id
    talla.save()
    estado = "habilitado" if talla.esta_activo else "inhabilitado"
    return JsonResponse({'success': True, 'mensaje': f'Talla de dotación {estado}.'})


# =============================================================================
# SUBMÓDULO: ELECTORAL
# =============================================================================

@login_required
@permiso_requerido('ver_electoral')  # 🆕
def configuracion_electoral(request):
    """Menú principal de configuración electoral."""
    return render(request, 'electoral/electoral_menu.html')


@login_required
@permiso_requerido('ver_centros_votacion')  # 🆕
def listar_centros_votaciones(request):
    """Listar centros de votación."""
    centros = CentroVotacion.objects.select_related('parroquia__municipio__estado').all().order_by('codigo_cne')
    return render(request, 'electoral/listar_centros_votaciones.html', {'centros': centros})


@login_required
@permiso_requerido('inhabilitar_centro')  # 🆕
@require_POST
def toggle_centro_votacion(request, centro_id):
    """Activar o inhabilitar un centro de votación."""
    try:
        centro = CentroVotacion.objects.get(id=centro_id)
        data = json.loads(request.body)
        nuevo_estatus = data.get('esta_activo', True)
        
        centro.esta_activo = nuevo_estatus
        centro.actualizado_por = request.user.id
        centro.save()
        
        estado_texto = "habilitado" if nuevo_estatus else "inhabilitado"
        return JsonResponse({'success': True, 'mensaje': f'El centro ha sido {estado_texto}.'})
    except CentroVotacion.DoesNotExist:
        return JsonResponse({'success': False, 'mensaje': 'El centro no existe.'})


@login_required
@permiso_requerido('importar_centros')  # 🆕
def importar_centros_votaciones(request):
    """Importar centros de votación desde archivo."""
    if request.method == 'POST' and request.FILES.get('archivo'):
        datos = obtener_datos_archivo(request.FILES['archivo'])
        if datos is None: 
            return JsonResponse({'success': False, 'mensaje': 'Formato no soportado.'})

        contador = 0
        errores = 0
        try:
            for fila in datos:
                if fila and len(fila) >= 5:
                    nom_est = str(fila[0]).strip()
                    nom_mun = str(fila[1]).strip()
                    nom_par = str(fila[2]).strip()
                    nom_cen = str(fila[3]).strip().upper()
                    cod_cne = str(fila[4]).strip().zfill(9)
                    
                    obj_par = Parroquia.objects.filter(
                        nombre_parroquia__iexact=nom_par,
                        municipio__nombre_municipio__iexact=nom_mun,
                        municipio__estado__nombre_estado__iexact=nom_est
                    ).first()
                    
                    if obj_par:
                        CentroVotacion.objects.update_or_create(
                            codigo_cne=cod_cne,
                            defaults={
                                'parroquia': obj_par,
                                'nombre_centro': nom_cen,
                                'esta_activo': True,
                                'creado_por': request.user.id,
                                'actualizado_por': request.user.id
                            }
                        )
                        contador += 1
                    else:
                        errores += 1
                        
            msj = f'¡Éxito! Se procesaron {contador} centros de votación.'
            if errores > 0:
                msj += f' No se encontraron {errores} ubicaciones geográficas referenciadas.'
                
            return JsonResponse({'success': True, 'mensaje': msj})
        except Exception as e:
            return JsonResponse({'success': False, 'mensaje': f'Error en procesamiento: {str(e)}'})
            
    return JsonResponse({'success': False, 'mensaje': 'Archivo no recibido.'})


# =============================================================================
# FUNCIONES AUXILIARES AJAX (PÚBLICAS PARA REGISTROS)
# =============================================================================

def get_centros_por_parroquia(request, parroquia_id):
    """Retorna centros de votación por parroquia (uso en formularios)."""
    from .models import CentroVotacion
    centros = CentroVotacion.objects.filter(parroquia_id=parroquia_id, esta_activo=True).values('id', 'nombre_centro').order_by('nombre_centro')
    return JsonResponse(list(centros), safe=False)