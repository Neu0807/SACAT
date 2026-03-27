--
-- PostgreSQL database dump
--

\restrict frgrlnZ7UzGqcyUa3HzpknDxcJMr1sgKoMaqMvAP0NMq2QrHKc0GsDecYktvxKo

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

-- Started on 2026-03-27 16:59:45

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 268 (class 1259 OID 16735)
-- Name: personas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.personas (
    id integer NOT NULL,
    tipo_doc_identificacion_id integer,
    cedula character varying(20) NOT NULL,
    primer_nombre character varying(50) NOT NULL,
    segundo_nombre character varying(50),
    primer_apellido character varying(50) NOT NULL,
    segundo_apellido character varying(50),
    es_naturalizado boolean DEFAULT false,
    nro_gaceta character varying(50),
    fecha_gaceta date,
    fecha_nacimiento date NOT NULL,
    lugar_nacimiento character varying(150),
    sexo_id integer,
    estado_civil_id integer,
    esta_activo boolean DEFAULT true,
    creado_por integer,
    actualizado_por integer,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.personas OWNER TO postgres;

--
-- TOC entry 267 (class 1259 OID 16734)
-- Name: personas_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.personas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.personas_id_seq OWNER TO postgres;

--
-- TOC entry 5143 (class 0 OID 0)
-- Dependencies: 267
-- Name: personas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.personas_id_seq OWNED BY public.personas.id;


--
-- TOC entry 4977 (class 2604 OID 16738)
-- Name: personas id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.personas ALTER COLUMN id SET DEFAULT nextval('public.personas_id_seq'::regclass);


--
-- TOC entry 5137 (class 0 OID 16735)
-- Dependencies: 268
-- Data for Name: personas; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.personas (id, tipo_doc_identificacion_id, cedula, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, es_naturalizado, nro_gaceta, fecha_gaceta, fecha_nacimiento, lugar_nacimiento, sexo_id, estado_civil_id, esta_activo, creado_por, actualizado_por, fecha_creacion, fecha_actualizacion) FROM stdin;
2	1	32556836	BRAULIO	JOSÉ	SEGURA	ARIAS	f	\N	\N	2008-02-14	CARACAS	2	5	t	2	2	2026-03-27 20:57:21.470239	2026-03-27 20:57:21.470252
\.


--
-- TOC entry 5144 (class 0 OID 0)
-- Dependencies: 267
-- Name: personas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.personas_id_seq', 2, true);


--
-- TOC entry 4983 (class 2606 OID 16751)
-- Name: personas personas_cedula_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.personas
    ADD CONSTRAINT personas_cedula_key UNIQUE (cedula);


--
-- TOC entry 4985 (class 2606 OID 16749)
-- Name: personas personas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.personas
    ADD CONSTRAINT personas_pkey PRIMARY KEY (id);


--
-- TOC entry 4986 (class 2606 OID 16762)
-- Name: personas personas_estado_civil_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.personas
    ADD CONSTRAINT personas_estado_civil_id_fkey FOREIGN KEY (estado_civil_id) REFERENCES public.estados_civiles(id);


--
-- TOC entry 4987 (class 2606 OID 16757)
-- Name: personas personas_sexo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.personas
    ADD CONSTRAINT personas_sexo_id_fkey FOREIGN KEY (sexo_id) REFERENCES public.sexos(id);


--
-- TOC entry 4988 (class 2606 OID 16752)
-- Name: personas personas_tipo_doc_identificacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.personas
    ADD CONSTRAINT personas_tipo_doc_identificacion_id_fkey FOREIGN KEY (tipo_doc_identificacion_id) REFERENCES public.tipos_docs_identificacion(id);


-- Completed on 2026-03-27 16:59:45

--
-- PostgreSQL database dump complete
--

\unrestrict frgrlnZ7UzGqcyUa3HzpknDxcJMr1sgKoMaqMvAP0NMq2QrHKc0GsDecYktvxKo

