import csv
import io
import openpyxl
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Estado, Municipio, Parroquia, TipoDocIdentificacion, Sexo, EstadoCivil, TipoContacto

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
        wb = openpyxl.load_workbook(archivo)
        hoja = wb.active
        return hoja.iter_rows(min_row=2, values_only=True)
    elif nombre_archivo.endswith('.csv'):
        try:
            contenido = archivo.read().decode('utf-8')
        except UnicodeDecodeError:
            archivo.seek(0)
            contenido = archivo.read().decode('latin-1')
        lector = csv.reader(io.StringIO(contenido))
        next(lector)  # Saltar encabezado
        return lector
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
                if fila and fila[0]:
                    Estado.objects.get_or_create(
                        nombre_estado=str(fila[0]).strip(),
                        defaults={'creado_por': request.user.id}
                    )
                    contador += 1
            return JsonResponse({'success': True, 'mensaje': f'Se procesaron {contador} registros de estados.'})
        except Exception as e:
            return JsonResponse({'success': False, 'mensaje': f'Error: {str(e)}'})
    return JsonResponse({'success': False, 'mensaje': 'Solicitud inválida.'})


@login_required
def importar_municipios(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'mensaje': 'Acceso denegado.'})
    
    if request.method == 'POST' and request.FILES.get('archivo'):
        datos = obtener_datos_archivo(request.FILES['archivo'])
        if datos is None: return JsonResponse({'success': False, 'mensaje': 'Formato no soportado.'})

        contador = 0
        try:
            for fila in datos:
                if fila and len(fila) >= 2:
                    nom_mun = str(fila[0]).strip()
                    nom_est = str(fila[1]).strip()
                    
                    obj_estado = Estado.objects.filter(nombre_estado__iexact=nom_est).first()
                    if obj_estado:
                        Municipio.objects.get_or_create(
                            nombre_municipio=nom_mun,
                            estado=obj_estado,
                            defaults={'creado_por': request.user.id}
                        )
                        contador += 1
            return JsonResponse({'success': True, 'mensaje': f'Se importaron {contador} municipios exitosamente.'})
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
        try:
            for fila in datos:
                if fila and len(fila) >= 3:
                    nom_par = str(fila[0]).strip()
                    nom_mun = str(fila[1]).strip()
                    nom_est = str(fila[2]).strip()
                    
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
            return JsonResponse({'success': True, 'mensaje': f'Se importaron {contador} parroquias exitosamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'mensaje': f'Error en procesamiento: {str(e)}'})
    return JsonResponse({'success': False, 'mensaje': 'Archivo no recibido.'})

# --- GESTIÓN DE IDENTIFICACIÓN ---

@login_required
def configuracion_identificacion(request):
    return render(request, 'configuracion/identificacion_menu.html')

@login_required
def listar_tipos_docs(request):
    documentos = TipoDocIdentificacion.objects.all().order_by('id')
    return render(request, 'configuracion/identificacion/listar_tipos_docs.html', {'documentos': documentos})

@login_required
@require_POST
def crear_tipo_documento(request):
    """Lógica AJAX para guardar un nuevo tipo de documento de identidad"""
    try:
        sigla = request.POST.get('sigla', '').strip().upper()
        descripcion = request.POST.get('descripcion', '').strip()
        ente_emisor = request.POST.get('ente_emisor', '').strip()
        aplica_a = request.POST.get('aplica_a', '').strip()

        if not sigla or not descripcion:
            return JsonResponse({'success': False, 'error': 'Sigla y Descripción son obligatorios.'})

        # Evitar duplicados por Sigla
        if TipoDocIdentificacion.objects.filter(sigla=sigla).exists():
            return JsonResponse({'success': False, 'error': f'La sigla "{sigla}" ya está registrada.'})

        # Guardado en DB (Ajustado a tu esquema SQL)
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
    return render(request, 'configuracion/identificacion/listar_sexos.html', {'sexos': sexos})

@login_required
def listar_estados_civiles(request):
    estados_civiles = EstadoCivil.objects.all().order_by('id')
    return render(request, 'configuracion/identificacion/listar_estados_civiles.html', {'estados_civiles': estados_civiles})

@login_required
def listar_tipos_contactos(request):
    contactos = TipoContacto.objects.all().order_by('id')
    return render(request, 'configuracion/identificacion/listar_tipos_contactos.html', {'contactos': contactos})