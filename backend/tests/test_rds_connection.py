#!/usr/bin/env python3
"""
Script de prueba de conexión a AWS RDS PostgreSQL
Autor: Sistema de Chatbot Provefut
Fecha: 2025-10-31

Este script verifica:
1. Conectividad con RDS
2. Existencia del esquema soporte_ti
3. Existencia de las 3 tablas principales
4. Integridad de las relaciones FK
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv
from typing import Optional

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message: str):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_header(message: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def test_connection(db_url: str) -> Optional[psycopg2.extensions.connection]:
    """Prueba la conexión a PostgreSQL"""
    print_header("TEST 1: Conexión a RDS")
    
    try:
        print_info(f"Conectando a: {db_url.split('@')[1] if '@' in db_url else 'PostgreSQL'}")
        conn = psycopg2.connect(db_url)
        
        # Obtener versión de PostgreSQL
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        
        print_success("Conexión establecida exitosamente")
        print_info(f"Versión: {version.split(',')[0]}")
        
        cur.close()
        return conn
        
    except Exception as e:
        print_error(f"Error de conexión: {str(e)}")
        return None

def test_schema(conn: psycopg2.extensions.connection) -> bool:
    """Verifica la existencia del esquema soporte_ti"""
    print_header("TEST 2: Esquema 'soporte_ti'")
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = 'soporte_ti'
        """)
        
        result = cur.fetchone()
        
        if result:
            print_success("Esquema 'soporte_ti' existe")
            cur.close()
            return True
        else:
            print_error("Esquema 'soporte_ti' NO encontrado")
            print_warning("Ejecuta el archivo schema.sql primero")
            cur.close()
            return False
            
    except Exception as e:
        print_error(f"Error al verificar esquema: {str(e)}")
        return False

def test_tables(conn: psycopg2.extensions.connection) -> bool:
    """Verifica la existencia de las tablas principales"""
    print_header("TEST 3: Tablas del Sistema")
    
    expected_tables = ['stticket', 'starchivos', 'stlogchat']
    
    try:
        cur = conn.cursor()
        
        all_exist = True
        for table in expected_tables:
            cur.execute("""
                SELECT table_name, table_type
                FROM information_schema.tables 
                WHERE table_schema = 'soporte_ti' 
                AND table_name = %s
            """, (table,))
            
            result = cur.fetchone()
            
            if result:
                print_success(f"Tabla '{table}' existe")
            else:
                print_error(f"Tabla '{table}' NO encontrada")
                all_exist = False
        
        cur.close()
        return all_exist
        
    except Exception as e:
        print_error(f"Error al verificar tablas: {str(e)}")
        return False

def test_table_structure(conn: psycopg2.extensions.connection):
    """Verifica la estructura de las tablas"""
    print_header("TEST 4: Estructura de Tablas")
    
    tables = {
        'stticket': ['ticket_cod_ticket', 'ticket_id_ticket', 'ticket_des_ticket', 
                     'ticket_est_ticket', 'ticket_fec_ticket'],
        'starchivos': ['archivo_cod_archivo', 'archivo_cod_ticket', 'archivo_nom_archivo'],
        'stlogchat': ['log_id', 'session_id', 'username', 'action_type']
    }
    
    try:
        cur = conn.cursor()
        
        for table, columns in tables.items():
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'soporte_ti' 
                AND table_name = %s
                ORDER BY ordinal_position
            """, (table,))
            
            db_columns = {row[0]: {'type': row[1], 'nullable': row[2]} 
                         for row in cur.fetchall()}
            
            print_info(f"\nTabla: {table}")
            
            for col in columns:
                if col in db_columns:
                    col_info = db_columns[col]
                    print_success(f"  • {col} ({col_info['type']}) - NULL: {col_info['nullable']}")
                else:
                    print_error(f"  • {col} - NO ENCONTRADA")
        
        cur.close()
        
    except Exception as e:
        print_error(f"Error al verificar estructura: {str(e)}")

def test_foreign_keys(conn: psycopg2.extensions.connection):
    """Verifica las relaciones FK"""
    print_header("TEST 5: Claves Foráneas (Foreign Keys)")
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                tc.constraint_name,
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'soporte_ti'
        """)
        
        fks = cur.fetchall()
        
        if fks:
            print_success(f"Encontradas {len(fks)} clave(s) foránea(s)")
            for fk in fks:
                print_info(f"  • {fk[1]}.{fk[2]} → {fk[3]}.{fk[4]}")
        else:
            print_warning("No se encontraron claves foráneas")
        
        cur.close()
        
    except Exception as e:
        print_error(f"Error al verificar FKs: {str(e)}")

def test_insert(conn: psycopg2.extensions.connection):
    """Prueba insertar y leer datos"""
    print_header("TEST 6: Inserción y Lectura de Datos")
    
    try:
        cur = conn.cursor()
        
        # Insertar ticket de prueba
        test_ticket_id = f"TKT-TEST-{os.getpid()}"
        
        cur.execute("""
            INSERT INTO soporte_ti.stticket 
            (ticket_id_ticket, ticket_des_ticket, ticket_tip_ticket, 
             ticket_est_ticket, ticket_asu_ticket, ticket_tusua_ticket)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING ticket_cod_ticket
        """, (test_ticket_id, 'Test de conexión', 'Software', 'PE', 
              'Test', 'test_user'))
        
        ticket_id = cur.fetchone()[0]
        conn.commit()
        
        print_success(f"Ticket insertado: {test_ticket_id} (ID: {ticket_id})")
        
        # Leer el ticket
        cur.execute("""
            SELECT ticket_id_ticket, ticket_des_ticket, ticket_est_ticket
            FROM soporte_ti.stticket
            WHERE ticket_cod_ticket = %s
        """, (ticket_id,))
        
        ticket = cur.fetchone()
        print_success(f"Ticket leído: {ticket[0]} - {ticket[1]}")
        
        # Eliminar el ticket de prueba
        cur.execute("""
            DELETE FROM soporte_ti.stticket 
            WHERE ticket_cod_ticket = %s
        """, (ticket_id,))
        conn.commit()
        
        print_success("Ticket de prueba eliminado")
        
        cur.close()
        
    except Exception as e:
        print_error(f"Error en test de inserción: {str(e)}")
        conn.rollback()

def main():
    """Función principal"""
    print("\n" + "="*60)
    print("🔍 TEST DE CONEXIÓN AWS RDS - CHATBOT PROVEFUT")
    print("="*60)
    
    # Cargar variables de entorno
    load_dotenv()
    
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print_error("Variable DATABASE_URL no encontrada en .env")
        print_info("Crea un archivo .env basándote en env.template")
        sys.exit(1)
    
    # Test 1: Conexión
    conn = test_connection(db_url)
    if not conn:
        sys.exit(1)
    
    # Test 2: Esquema
    schema_exists = test_schema(conn)
    if not schema_exists:
        conn.close()
        sys.exit(1)
    
    # Test 3: Tablas
    tables_exist = test_tables(conn)
    
    # Test 4: Estructura
    test_table_structure(conn)
    
    # Test 5: Foreign Keys
    test_foreign_keys(conn)
    
    # Test 6: Inserción
    if tables_exist:
        test_insert(conn)
    
    # Cerrar conexión
    conn.close()
    
    # Resumen final
    print_header("RESUMEN")
    
    if tables_exist:
        print_success("Todos los tests pasaron correctamente")
        print_info("La base de datos está lista para usarse")
        sys.exit(0)
    else:
        print_warning("Algunos tests fallaron")
        print_info("Revisa los errores arriba y ejecuta schema.sql")
        sys.exit(1)

if __name__ == "__main__":
    main()

