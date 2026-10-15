-- ============================================================================
-- SCRIPT DE ACTUALIZACIÓN - MÓDULO FORMACIÓN SACAT
-- Fecha: 2026-10-14
-- ============================================================================

-- 1. TABLA: motivos_rechazo (NUEVA)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.motivos_rechazo (
    id integer NOT NULL,
    descripcion varchar(200) NOT NULL,
    esta_activo boolean DEFAULT true,
    creado_por integer,
    actualizado_por integer,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE IF NOT EXISTS public.motivos_rechazo_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

ALTER TABLE public.motivos_rechazo
    ALTER COLUMN id SET DEFAULT nextval('public.motivos_rechazo_id_seq'::regclass);

ALTER TABLE public.motivos_rechazo DROP CONSTRAINT IF EXISTS motivos_rechazo_pkey;
ALTER TABLE public.motivos_rechazo ADD CONSTRAINT motivos_rechazo_pkey PRIMARY KEY (id);

INSERT INTO public.motivos_rechazo (descripcion, esta_activo) VALUES
('Cupo máximo alcanzado', true),
('Perfil no cumple con los requisitos del curso', true),
('Trabajador no pertenece al área objetivo', true),
('Solicitud duplicada', true),
('Postulación fuera de fecha', true),
('Otro (especificar en observaciones)', true)
ON CONFLICT DO NOTHING;

-- 2. Agregar motivo_rechazo_id a postulaciones
-- ============================================================================
ALTER TABLE public.postulaciones
    ADD COLUMN IF NOT EXISTS motivo_rechazo_id integer NULL;

ALTER TABLE public.postulaciones
    DROP CONSTRAINT IF EXISTS postulaciones_motivo_rechazo_id_fkey;
ALTER TABLE public.postulaciones
    ADD CONSTRAINT postulaciones_motivo_rechazo_id_fkey
    FOREIGN KEY (motivo_rechazo_id) REFERENCES public.motivos_rechazo(id);

-- 3. TABLA: certificados (NUEVA)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.certificados (
    id integer NOT NULL,
    postulacion_id integer NOT NULL,
    ruta_archivo varchar(255) NOT NULL,
    cargado_por integer,
    origen varchar(20) NOT NULL DEFAULT 'GH',
    version integer DEFAULT 1,
    esta_activo boolean DEFAULT true,
    reemplaza_a_id integer,
    motivo_reemplazo text,
    observaciones text,
    creado_por integer,
    actualizado_por integer,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE IF NOT EXISTS public.certificados_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

ALTER TABLE public.certificados
    ALTER COLUMN id SET DEFAULT nextval('public.certificados_id_seq'::regclass);

ALTER TABLE public.certificados DROP CONSTRAINT IF EXISTS certificados_pkey;
ALTER TABLE public.certificados ADD CONSTRAINT certificados_pkey PRIMARY KEY (id);

ALTER TABLE public.certificados
    DROP CONSTRAINT IF EXISTS certificados_postulacion_id_fkey;
ALTER TABLE public.certificados
    ADD CONSTRAINT certificados_postulacion_id_fkey
    FOREIGN KEY (postulacion_id) REFERENCES public.postulaciones(id);

CREATE UNIQUE INDEX IF NOT EXISTS certificados_postulacion_uniq
    ON public.certificados (postulacion_id)
    WHERE esta_activo = true;

-- 4. Historial de estados de postulación (NUEVA - para trazabilidad)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.historial_estados_postulacion (
    id integer NOT NULL,
    postulacion_id integer NOT NULL,
    estado_anterior varchar(30),
    estado_nuevo varchar(30) NOT NULL,
    cambiado_por integer,
    motivo text,
    fecha_cambio timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    creado_por integer,
    actualizado_por integer,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE IF NOT EXISTS public.historial_estados_postulacion_id_seq
    AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

ALTER TABLE public.historial_estados_postulacion
    ALTER COLUMN id SET DEFAULT nextval('public.historial_estados_postulacion_id_seq'::regclass);

ALTER TABLE public.historial_estados_postulacion
    DROP CONSTRAINT IF EXISTS historial_estados_postulacion_pkey;
ALTER TABLE public.historial_estados_postulacion
    ADD CONSTRAINT historial_estados_postulacion_pkey PRIMARY KEY (id);

ALTER TABLE public.historial_estados_postulacion
    DROP CONSTRAINT IF EXISTS historial_estados_postulacion_postulacion_id_fkey;
ALTER TABLE public.historial_estados_postulacion
    ADD CONSTRAINT historial_estados_postulacion_postulacion_id_fkey
    FOREIGN KEY (postulacion_id) REFERENCES public.postulaciones(id);

-- 5. Permisos nuevos
-- ============================================================================
INSERT INTO public.permisos_sis (nombre_permiso, descripcion, esta_activo, fecha_creacion, fecha_actualizacion)
VALUES
('gestionar_grupos_formacion', 'Crear y editar grupos de formación', true, NOW(), NOW()),
('cargar_asistencia_formacion', 'Registrar asistencia a grupos de formación', true, NOW(), NOW()),
('agregar_asistente_en_sitio', 'Agregar asistentes no planificados en sitio', true, NOW(), NOW()),
('sustituir_postulacion', 'Sustituir un participante aprobado por otro', true, NOW(), NOW()),
('inscribir_trabajador_directo', 'Inscribir directamente a un trabajador en una oferta', true, NOW(), NOW()),
('cargar_certificado_gh', 'Cargar certificados como Gestión Humana', true, NOW(), NOW()),
('descargar_certificado', 'Descargar certificados de formación', true, NOW(), NOW()),
('cargar_certificado_propio', 'Cargar certificado propio de formación', true, NOW(), NOW()),
('ver_dashboard_formacion', 'Ver dashboard de indicadores de formación', true, NOW(), NOW()),
('finalizar_oferta', 'Marcar oferta de formación como finalizada', true, NOW(), NOW())
ON CONFLICT (nombre_permiso) DO NOTHING;

-- 6. Asignar permisos a GH (rol_id = 4)
-- ============================================================================
INSERT INTO public.roles_permisos (rol_id, permiso_sis_id, esta_activo, fecha_creacion, fecha_actualizacion)
SELECT 4, id, true, NOW(), NOW()
FROM public.permisos_sis
WHERE nombre_permiso IN (
    'gestionar_grupos_formacion', 'cargar_asistencia_formacion',
    'agregar_asistente_en_sitio', 'sustituir_postulacion',
    'inscribir_trabajador_directo', 'cargar_certificado_gh',
    'descargar_certificado', 'finalizar_oferta', 'ver_dashboard_formacion'
)
AND NOT EXISTS (
    SELECT 1 FROM public.roles_permisos rp
    WHERE rp.rol_id = 4 AND rp.permiso_sis_id = public.permisos_sis.id
);

-- 7. Asignar permisos a Trabajador (rol_id = 3)
-- ============================================================================
INSERT INTO public.roles_permisos (rol_id, permiso_sis_id, esta_activo, fecha_creacion, fecha_actualizacion)
SELECT 3, id, true, NOW(), NOW()
FROM public.permisos_sis
WHERE nombre_permiso IN ('cargar_certificado_propio', 'descargar_certificado')
AND NOT EXISTS (
    SELECT 1 FROM public.roles_permisos rp
    WHERE rp.rol_id = 3 AND rp.permiso_sis_id = public.permisos_sis.id
);

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================