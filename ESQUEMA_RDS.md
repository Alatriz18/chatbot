# 🗃️ Esquema de Base de Datos RDS PostgreSQL

**Base de Datos:** `chatbot_provefut`  
**Esquema:** `soporte_ti`  
**Versión:** PostgreSQL 15.14  
**Endpoint:** chatbot-provefut-db.cyfwq6kgermb.us-east-1.rds.amazonaws.com

---

## 📊 Diagrama del Esquema

```
┌─────────────────────────────────────────────────────────────┐
│                    ESQUEMA: soporte_ti                      │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                        stticket                              │
│ ─────────────────────────────────────────────────────────── │
│ PK  ticket_cod_ticket        SERIAL                          │
│ UQ  ticket_id_ticket         VARCHAR(50)  (TKT-YYYYMMDD...)  │
│     ticket_des_ticket        TEXT          (Descripción)     │
│     ticket_tip_ticket        VARCHAR(20)   (Software/Hardware)│
│     ticket_est_ticket        VARCHAR(2)    (PE/PR/FN)        │
│     ticket_asu_ticket        VARCHAR(255)  (Asunto)          │
│     ticket_tusua_ticket      VARCHAR(100)  (Usuario)         │
│     ticket_cie_ticket        INTEGER       (User code)       │
│     ticket_asignado_a        VARCHAR(100)  (Admin asignado)  │
│     ticket_preferencia_usuario VARCHAR(100)                  │
│     ticket_fec_ticket        TIMESTAMP     (Fecha creación)  │
│     ticket_calificacion      INTEGER       (1-5 estrellas)   │
│     ticket_comentarios       TEXT                            │
│     ticket_fec_cierre        TIMESTAMP                       │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                       starchivos                             │
│ ─────────────────────────────────────────────────────────── │
│ PK  archivo_cod_archivo      SERIAL                          │
│ FK  archivo_cod_ticket       INTEGER  → stticket             │
│     archivo_nom_archivo      VARCHAR(255)  (Nombre original) │
│     archivo_tip_archivo      VARCHAR(20)   (pdf, png, jpg)   │
│     archivo_tam_archivo      BIGINT        (Tamaño en bytes) │
│     archivo_rut_archivo      VARCHAR(500)  (Ruta del archivo)│
│     archivo_usua_archivo     VARCHAR(100)  (Usuario que subió)│
│     archivo_fec_archivo      TIMESTAMP     (Fecha de subida) │
└──────────────────────────────────────────────────────────────┘


┌──────────────────────────────────────────────────────────────┐
│                       stlogchat                              │
│ ─────────────────────────────────────────────────────────── │
│ PK  log_id                   SERIAL                          │
│     session_id               VARCHAR(100)  (ID de sesión)    │
│     username                 VARCHAR(100)  (Usuario)         │
│     action_type              VARCHAR(50)   (Tipo de acción)  │
│     action_value             TEXT          (Valor de acción) │
│     bot_response             TEXT          (Respuesta del bot)│
│     timestamp                TIMESTAMP     (Fecha/hora)      │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔑 Tabla: stticket (Tickets de Soporte)

**Propósito:** Almacena todos los tickets de soporte técnico

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `ticket_cod_ticket` | SERIAL (PK) | ID numérico único | 1, 2, 3... |
| `ticket_id_ticket` | VARCHAR(50) | ID legible | TKT-20251031-123456 |
| `ticket_des_ticket` | TEXT | Descripción del problema | "Mi computador está lento..." |
| `ticket_tip_ticket` | VARCHAR(20) | Tipo de ticket | Software / Hardware |
| `ticket_est_ticket` | VARCHAR(2) | Estado | PE (Pendiente) / PR (En Proceso) / FN (Finalizado) |
| `ticket_asu_ticket` | VARCHAR(255) | Asunto/Categoría | "Equipo lento" |
| `ticket_tusua_ticket` | VARCHAR(100) | Usuario que creó el ticket | "samuel.solano" |
| `ticket_cie_ticket` | INTEGER | Código de usuario (legacy) | 1001 |
| `ticket_asignado_a` | VARCHAR(100) | Admin asignado | "admin.usuario" |
| `ticket_preferencia_usuario` | VARCHAR(100) | Admin preferido por usuario | "admin.usuario" o null |
| `ticket_fec_ticket` | TIMESTAMP | Fecha de creación | 2025-10-31 13:45:32 |
| `ticket_calificacion` | INTEGER | Calificación del servicio | 1, 2, 3, 4, 5 |
| `ticket_comentarios` | TEXT | Comentarios adicionales | null |
| `ticket_fec_cierre` | TIMESTAMP | Fecha de cierre | null o fecha |

**Índices:**
- `idx_ticket_usuario` - Búsqueda por usuario
- `idx_ticket_asignado` - Búsqueda por admin asignado
- `idx_ticket_estado` - Filtro por estado
- `idx_ticket_fecha` - Ordenamiento por fecha

---

## 📎 Tabla: starchivos (Archivos Adjuntos)

**Propósito:** Almacena metadatos de archivos adjuntos a tickets

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `archivo_cod_archivo` | SERIAL (PK) | ID único del archivo | 1, 2, 3... |
| `archivo_cod_ticket` | INTEGER (FK) | Referencia al ticket | 1 → ticket_cod_ticket |
| `archivo_nom_archivo` | VARCHAR(255) | Nombre original | "captura_error.png" |
| `archivo_tip_archivo` | VARCHAR(20) | Extensión | pdf, png, jpg, xlsx |
| `archivo_tam_archivo` | BIGINT | Tamaño en bytes | 1024000 (1MB) |
| `archivo_rut_archivo` | VARCHAR(500) | Ruta relativa | "TKT-XXX/uuid.png" |
| `archivo_usua_archivo` | VARCHAR(100) | Usuario que subió | "samuel.solano" |
| `archivo_fec_archivo` | TIMESTAMP | Fecha de subida | 2025-10-31 13:45:32 |

**Relación:**
- `archivo_cod_ticket` → `stticket.ticket_cod_ticket` (CASCADE DELETE)

**Índices:**
- `idx_archivo_ticket` - Búsqueda por ticket
- `idx_archivo_fecha` - Ordenamiento por fecha

---

## 💬 Tabla: stlogchat (Logs de Interacciones)

**Propósito:** Registra todas las interacciones del chatbot para análisis

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `log_id` | SERIAL (PK) | ID único del log | 1, 2, 3... |
| `session_id` | VARCHAR(100) | ID de sesión | "sess_abc123..." |
| `username` | VARCHAR(100) | Usuario | "samuel.solano" |
| `action_type` | VARCHAR(50) | Tipo de acción | "select_category", "create_ticket" |
| `action_value` | TEXT | Valor de la acción | JSON o texto |
| `bot_response` | TEXT | Respuesta del bot | "¿Cuál es tu problema?" |
| `timestamp` | TIMESTAMP | Fecha/hora | 2025-10-31 13:45:32 |

**Índices:**
- `idx_log_session` - Búsqueda por sesión
- `idx_log_usuario` - Búsqueda por usuario
- `idx_log_fecha` - Ordenamiento por fecha
- `idx_log_action` - Filtro por tipo de acción

---

## 🔗 Relaciones

```
stticket (1) ──────── (N) starchivos
    │
    │ Un ticket puede tener múltiples archivos
    │ Si se elimina un ticket, se eliminan sus archivos (CASCADE)
    │

stlogchat
    │
    │ Tabla independiente, no tiene relaciones FK
    │ Se usa solo para análisis
```

---

## 📈 Datos Actuales

```sql
-- Tickets: 3
SELECT COUNT(*) FROM soporte_ti.stticket;
-- Resultado: 3

-- Archivos: 0
SELECT COUNT(*) FROM soporte_ti.starchivos;
-- Resultado: 0

-- Logs: 0
SELECT COUNT(*) FROM soporte_ti.stlogchat;
-- Resultado: 0
```

---

## 🔍 Consultas Útiles

### Ver todos los tickets pendientes
```sql
SELECT 
    ticket_id_ticket,
    ticket_asu_ticket,
    ticket_tusua_ticket,
    ticket_est_ticket,
    ticket_fec_ticket
FROM soporte_ti.stticket
WHERE ticket_est_ticket = 'PE'
ORDER BY ticket_fec_ticket DESC;
```

### Ver tickets con archivos adjuntos
```sql
SELECT 
    t.ticket_id_ticket,
    t.ticket_asu_ticket,
    COUNT(a.archivo_cod_archivo) as num_archivos
FROM soporte_ti.stticket t
LEFT JOIN soporte_ti.starchivos a ON t.ticket_cod_ticket = a.archivo_cod_ticket
GROUP BY t.ticket_cod_ticket
HAVING COUNT(a.archivo_cod_archivo) > 0;
```

### Ver actividad del chatbot por usuario
```sql
SELECT 
    username,
    action_type,
    COUNT(*) as total_acciones
FROM soporte_ti.stlogchat
GROUP BY username, action_type
ORDER BY total_acciones DESC;
```

### Tickets por admin con carga de trabajo
```sql
SELECT 
    ticket_asignado_a,
    COUNT(*) as tickets_asignados,
    COUNT(CASE WHEN ticket_est_ticket = 'PE' THEN 1 END) as pendientes,
    COUNT(CASE WHEN ticket_est_ticket = 'FN' THEN 1 END) as finalizados
FROM soporte_ti.stticket
WHERE ticket_asignado_a IS NOT NULL
GROUP BY ticket_asignado_a
ORDER BY tickets_asignados DESC;
```

---

## 💾 Conexión

**String de conexión:**
```
postgresql://postgres:ChatbotProvefut2025!@chatbot-provefut-db.cyfwq6kgermb.us-east-1.rds.amazonaws.com:5432/chatbot_provefut
```

**Con psql:**
```bash
psql -h chatbot-provefut-db.cyfwq6kgermb.us-east-1.rds.amazonaws.com \
     -U postgres \
     -d chatbot_provefut
```

**Con Python:**
```python
import psycopg2
import os

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute("SELECT * FROM soporte_ti.stticket")
tickets = cur.fetchall()
```

---

## 📊 Tamaño y Capacidad

- **Almacenamiento**: 20 GB gp3 (3000 IOPS)
- **Clase**: db.t3.micro (2 vCPU, 1 GB RAM)
- **Backup**: 7 días de retención
- **Región**: us-east-1
- **Multi-AZ**: No (Single AZ)
- **Encriptación**: Habilitada (AWS KMS)

---

## 🎯 Resumen

- **3 tablas** principales
- **14 índices** para optimización
- **1 relación** FK (tickets → archivos)
- **Escalable** y lista para producción
- **Backup** automático diario

---

¡Esquema simple y eficiente! 🚀

