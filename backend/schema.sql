-- =====================================================
-- ESQUEMA DE BASE DE DATOS PARA CHATBOT PROVEFUT
-- Sistema de Soporte TI - AWS RDS PostgreSQL
-- =====================================================
-- 
-- Este script crea el esquema completo para el sistema de tickets
-- SIN incluir autenticación (se usará AWS Cognito posteriormente)
--

-- Crear el esquema si no existe
CREATE SCHEMA IF NOT EXISTS soporte_ti;

-- =====================================================
-- TABLA: stticket
-- Descripción: Almacena todos los tickets de soporte generados
-- =====================================================

CREATE TABLE IF NOT EXISTS soporte_ti.stticket (
    -- Identificador único autoincremental (PRIMARY KEY)
    ticket_cod_ticket SERIAL PRIMARY KEY,
    
    -- ID del ticket en formato TKT-YYYYMMDD-HHMMSS
    ticket_id_ticket VARCHAR(50) UNIQUE NOT NULL,
    
    -- Descripción completa del problema
    ticket_des_ticket TEXT NOT NULL,
    
    -- Tipo de ticket: 'Software' o 'Hardware'
    ticket_tip_ticket VARCHAR(20) NOT NULL CHECK (ticket_tip_ticket IN ('Software', 'Hardware')),
    
    -- Estado del ticket: 'PE' (Pendiente), 'PR' (En Proceso), 'FN' (Finalizado)
    ticket_est_ticket VARCHAR(2) NOT NULL DEFAULT 'PE' CHECK (ticket_est_ticket IN ('PE', 'PR', 'FN')),
    
    -- Asunto o categoría del ticket
    ticket_asu_ticket VARCHAR(255),
    
    -- Usuario que creó el ticket (username)
    ticket_tusua_ticket VARCHAR(100) NOT NULL,
    
    -- Código del usuario (user_code de Informix, se mantendrá para compatibilidad)
    ticket_cie_ticket INTEGER,
    
    -- Administrador asignado al ticket
    ticket_asignado_a VARCHAR(100),
    
    -- Preferencia del usuario sobre qué admin le atienda
    ticket_preferencia_usuario VARCHAR(100),
    
    -- Fecha y hora de creación del ticket
    ticket_fec_ticket TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Calificación del servicio (1-5 estrellas)
    ticket_calificacion INTEGER CHECK (ticket_calificacion >= 1 AND ticket_calificacion <= 5),
    
    -- Comentarios adicionales del usuario
    ticket_comentarios TEXT,
    
    -- Fecha de cierre del ticket
    ticket_fec_cierre TIMESTAMP,
    
    -- Índices para mejorar el rendimiento
    CONSTRAINT idx_ticket_id UNIQUE (ticket_id_ticket)
);

-- Índices adicionales para optimización de consultas
CREATE INDEX idx_ticket_usuario ON soporte_ti.stticket(ticket_tusua_ticket);
CREATE INDEX idx_ticket_asignado ON soporte_ti.stticket(ticket_asignado_a);
CREATE INDEX idx_ticket_estado ON soporte_ti.stticket(ticket_est_ticket);
CREATE INDEX idx_ticket_fecha ON soporte_ti.stticket(ticket_fec_ticket DESC);

-- =====================================================
-- TABLA: starchivos
-- Descripción: Almacena metadatos de archivos adjuntos a tickets
-- =====================================================

CREATE TABLE IF NOT EXISTS soporte_ti.starchivos (
    -- Identificador único del archivo
    archivo_cod_archivo SERIAL PRIMARY KEY,
    
    -- FK al ticket al que pertenece este archivo
    archivo_cod_ticket INTEGER NOT NULL,
    
    -- Nombre original del archivo
    archivo_nom_archivo VARCHAR(255) NOT NULL,
    
    -- Tipo/extensión del archivo (pdf, png, jpg, etc.)
    archivo_tip_archivo VARCHAR(20) NOT NULL,
    
    -- Tamaño del archivo en bytes
    archivo_tam_archivo BIGINT NOT NULL,
    
    -- Ruta relativa del archivo en el sistema de archivos (ej: TKT-XXX/uuid.pdf)
    archivo_rut_archivo VARCHAR(500) NOT NULL,
    
    -- Usuario que subió el archivo
    archivo_usua_archivo VARCHAR(100) NOT NULL,
    
    -- Fecha de subida
    archivo_fec_archivo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraint de clave foránea
    CONSTRAINT fk_archivo_ticket FOREIGN KEY (archivo_cod_ticket) 
        REFERENCES soporte_ti.stticket(ticket_cod_ticket) 
        ON DELETE CASCADE
);

-- Índices para optimizar consultas de archivos
CREATE INDEX idx_archivo_ticket ON soporte_ti.starchivos(archivo_cod_ticket);
CREATE INDEX idx_archivo_fecha ON soporte_ti.starchivos(archivo_fec_archivo DESC);

-- =====================================================
-- TABLA: stlogchat
-- Descripción: Almacena logs de interacciones del chatbot
-- =====================================================

CREATE TABLE IF NOT EXISTS soporte_ti.stlogchat (
    -- Identificador único del log
    log_id SERIAL PRIMARY KEY,
    
    -- ID de sesión del usuario
    session_id VARCHAR(100) NOT NULL,
    
    -- Nombre del usuario
    username VARCHAR(100) NOT NULL,
    
    -- Tipo de acción realizada (ej: 'select_category', 'create_ticket', etc.)
    action_type VARCHAR(50) NOT NULL,
    
    -- Valor de la acción (puede ser JSON o texto)
    action_value TEXT,
    
    -- Respuesta del bot
    bot_response TEXT,
    
    -- Timestamp de la interacción
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para análisis de interacciones
CREATE INDEX idx_log_session ON soporte_ti.stlogchat(session_id);
CREATE INDEX idx_log_usuario ON soporte_ti.stlogchat(username);
CREATE INDEX idx_log_fecha ON soporte_ti.stlogchat(timestamp DESC);
CREATE INDEX idx_log_action ON soporte_ti.stlogchat(action_type);

-- =====================================================
-- COMENTARIOS EN LAS TABLAS (Documentación)
-- =====================================================

COMMENT ON TABLE soporte_ti.stticket IS 'Tabla principal de tickets de soporte técnico';
COMMENT ON TABLE soporte_ti.starchivos IS 'Metadatos de archivos adjuntos a tickets';
COMMENT ON TABLE soporte_ti.stlogchat IS 'Logs de interacciones del chatbot para análisis';

-- =====================================================
-- DATOS DE PRUEBA (OPCIONAL - Comentar si no se necesita)
-- =====================================================

-- Ticket de ejemplo
INSERT INTO soporte_ti.stticket 
    (ticket_id_ticket, ticket_des_ticket, ticket_tip_ticket, ticket_est_ticket, 
     ticket_asu_ticket, ticket_tusua_ticket, ticket_cie_ticket)
VALUES 
    ('TKT-20251031-000001', 'Ticket de prueba del sistema', 'Software', 'FN', 
     'Prueba de instalación', 'sistema', 0);

-- =====================================================
-- VERIFICACIÓN DEL ESQUEMA
-- =====================================================

-- Consultar todas las tablas creadas
SELECT 
    table_schema, 
    table_name, 
    table_type
FROM 
    information_schema.tables 
WHERE 
    table_schema = 'soporte_ti'
ORDER BY 
    table_name;

-- Fin del script

