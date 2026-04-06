import csv
import io
import openpyxl
import json  # <--- Aquí está el salvavidas para el error
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import (
    Estado, Municipio, Parroquia, TipoDocIdentificacion, 
    Sexo, EstadoCivil, TipoContacto, CentroVotacion  # <--- AGREGA ESTE ÚLTIMO
)

# --- VISTAS DE NAVEGACIÓN ---

@login_required
def configuracion_ubicacion(request):
    return render(request, 'configuracion/ubicacion_menu.html')

@login_required
def listar_estados(request):
    estados = Estado.objects.all().order_by('nombre_estado')
    return render(request, 'configuracion/ubicacion/listar_estados.html', {'estados': estados})

@login_required
def listar_municipios(request):
    municipios = Municipio.objects.select_related('estado').all().order_by('estado__nombre_estado', 'nombre_municipio')
    return render(request, 'configuracion/ubicacion/listar_municipios.html', {'municipios': municipios})

@login_required
def listar_parroquias(request):
    parroquias = Parroquia.objects.select_related('municipio__estado').all().order_by('municipio__estado__nombre_estado', 'nombre_parroquia')
    return render(request, 'configuracion/ubicacion/listar_parroquias.html', {'parroquias': parroquias})


# --- LÓGICA DE APOYO PARA IMPORTACIÓN ---

def obtener_datos_archivo(archivo):
    """Función auxiliar para normalizar la lectura de Excel y CSV"""
    nombre_archivo = archivo.name.lower()
    if nombre_archivo.endswith(('.xlsx', '.xls')):
        try:
            wb = openpyxl.load_workbook(archivo, data_only=True)
            hoja = wb.active
            # iter_rows con min_row=2 salta el encabezado
            return list(hoja.iter_rows(min_row=2, values_only=True))
        except Exception:
            return None
    elif nombre_archivo.endswith('.csv'):
        try:
            # utf-8-sig maneja archivos guardados desde Excel con BOM
            contenido = archivo.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            archivo.seek(0)
            contenido = archivo.read().decode('latin-1')
        
        lector = csv.reader(io.StringIO(contenido))
        next(lector, None)  # Saltar encabezado
        return list(lector)
    return None


# --- VISTAS DE IMPORTACIÓN ---

@login_required
def importar_estados(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'mensaje': 'Acceso denegado.'})
    
    if request.method == 'POST' and request.FILES.get('archivo'):
        datos = obtener_datos_archivo(request.FILES['archivo'])
        if datos is None:
            return JsonResponse({'success': False, 'mensaje': 'Formato no soportado.'})

        contador = 0
        try:
            for fila in datos:
                # fila[0] es NOMBRE en tu CSV
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


@login_required
def importar_municipios(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'mensaje': 'Acceso denegado.'})
    
    if request.method == 'POST' and request.FILES.get('archivo'):
        datos = obtener_datos_archivo(request.FILES['archivo'])
        if datos is None: 
            return JsonResponse({'success': False, 'mensaje': 'Formato no soportado.'})

        contador = 0
        errores = 0
        try:
            for fila in datos:
                # Tu CSV tiene: ESTADO (fila[0]), NOMBRE (fila[1])
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


@login_required
def importar_parroquias(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'mensaje': 'Acceso denegado.'})
    
    if request.method == 'POST' and request.FILES.get('archivo'):
        datos = obtener_datos_archivo(request.FILES['archivo'])
        if datos is None: return JsonResponse({'success': False, 'mensaje': 'Formato no soportado.'})

        contador = 0
        errores = 0
        try:
            for fila in datos:
                # Estructura de TU archivo: ESTADO(0), MUNICIPIO(1), PARROQUIA(2)
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


# --- VISTAS DE ACCIONES AJAX (TOGGLE ESTATUS) ---

@login_required
@require_POST
def toggle_municipio(request, municipio_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'mensaje': 'Acceso denegado.'})
    
    try:
        municipio = Municipio.objects.get(id=municipio_id)
        # Obtenemos el nuevo estado del body del fetch
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
@require_POST
def toggle_estado(request, estado_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'mensaje': 'Acceso denegado.'})
    
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


# --- GESTIÓN DE IDENTIFICACIÓN ---

@login_required
def configuracion_identidad(request):
    return render(request, 'configuracion/identidad_menu.html')

@login_required
def listar_tipos_docs(request):
    documentos = TipoDocIdentificacion.objects.all().order_by('id')
    # CAMBIO: 'identificacion' -> 'identidad'
    return render(request, 'configuracion/identidad/listar_tipos_docs.html', {'documentos': documentos})

@login_required
@require_POST
def crear_tipo_documento(request):
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
def listar_sexos(request):
    sexos = Sexo.objects.all().order_by('id')
    # CAMBIO: 'identificacion' -> 'identidad'
    return render(request, 'configuracion/identidad/listar_sexos.html', {'sexos': sexos})

@login_required
def listar_estados_civiles(request):
    estados_civiles = EstadoCivil.objects.all().order_by('id')
    # CAMBIO: 'identificacion' -> 'identidad'
    return render(request, 'configuracion/identidad/listar_estados_civiles.html', {'estados_civiles': estados_civiles})

@login_required
def listar_tipos_contactos(request):
    contactos = TipoContacto.objects.all().order_by('id')
    # CAMBIO: 'identificacion' -> 'identidad'
    return render(request, 'configuracion/identidad/listar_tipos_contactos.html', {'contactos': contactos})

@login_required
@require_POST
def toggle_parroquia(request, parroquia_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'mensaje': 'Acceso denegado.'})
    
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
def configuracion_institucion(request):
    return render(request, 'configuracion/institucion_menu.html')

@login_required
def configuracion_estructura(request):
    return render(request, 'configuracion/estructura_menu.html')

@login_required
def configuracion_laboral(request):
    return render(request, 'configuracion/laboral_menu.html')

@login_required
def configuracion_entorno(request):
    return render(request, 'configuracion/entorno_menu.html')

@login_required
def configuracion_dotacion(request):
    return render(request, 'configuracion/dotacion_menu.html')

@login_required
def configuracion_electoral(request):
    return render(request, 'configuracion/electoral_menu.html')


@login_required
@require_POST
def toggle_tipo_doc(request, doc_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'mensaje': 'Acceso denegado.'})
    
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
    
@login_required
@require_POST
def editar_tipo_documento(request, doc_id):
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
def listar_centros_votaciones(request):
    # Usamos select_related para traer la jerarquía geográfica en una sola consulta
    centros = CentroVotacion.objects.select_related('parroquia__municipio__estado').all().order_by('codigo_cne')
    return render(request, 'configuracion/centros_votaciones/listar_centros_votaciones.html', {'centros': centros})

@login_required
@require_POST
def toggle_centro_votacion(request, centro_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'mensaje': 'Acceso denegado.'})
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
def importar_centros_votaciones(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'mensaje': 'Acceso denegado.'})
    
    if request.method == 'POST' and request.FILES.get('archivo'):
        datos = obtener_datos_archivo(request.FILES['archivo'])
        if datos is None: 
            return JsonResponse({'success': False, 'mensaje': 'Formato no soportado.'})

        contador = 0
        errores = 0
        try:
            for fila in datos:
                # Estructura del archivo: ESTADO(0), MUNICIPIO(1), PARROQUIA(2), NOMBRE(3), CODIGO(4)
                if fila and len(fila) >= 5:
                    nom_est = str(fila[0]).strip()
                    nom_mun = str(fila[1]).strip()
                    nom_par = str(fila[2]).strip()
                    nom_cen = str(fila[3]).strip().upper()
                    # zfill(9) para asegurar que el código CNE no pierda el cero inicial
                    cod_cne = str(fila[4]).strip().zfill(9)
                    
                    # Buscamos la parroquia exacta
                    obj_par = Parroquia.objects.filter(
                        nombre_parroquia__iexact=nom_par,
                        municipio__nombre_municipio__iexact=nom_mun,
                        municipio__estado__nombre_estado__iexact=nom_est
                    ).first()
                    
                    if obj_par:
                        # Usamos update_or_create para evitar duplicados si se resube el archivo
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
    
def get_centros_por_parroquia(request, parroquia_id):
    from .models import CentroVotacion
    centros = CentroVotacion.objects.filter(parroquia_id=parroquia_id, esta_activo=True).values('id', 'nombre_centro').order_by('nombre_centro')
    return JsonResponse(list(centros), safe=False)
