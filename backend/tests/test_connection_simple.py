#!/usr/bin/env python3
"""
Script simplificado de prueba de conexión a AWS RDS PostgreSQL
Compatible con Windows PowerShell
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv

def test_connection():
    """Prueba la conexión y estructura de la base de datos"""
    print("="*60)
    print("TEST DE CONEXION AWS RDS - CHATBOT PROVEFUT")
    print("="*60)
    print()
    
    # Cargar variables de entorno
    load_dotenv()
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print("[ERROR] Variable DATABASE_URL no encontrada en .env")
        return False
    
    print("[INFO] Conectando a RDS...")
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Test 1: Versión de PostgreSQL
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"[OK] Conexion establecida")
        print(f"[INFO] Version: {version.split(',')[0]}")
        print()
        
        # Test 2: Verificar esquema
        cur.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = 'soporte_ti'
        """)
        if cur.fetchone():
            print("[OK] Esquema 'soporte_ti' existe")
        else:
            print("[ERROR] Esquema 'soporte_ti' NO encontrado")
            return False
        
        # Test 3: Verificar tablas
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'soporte_ti'
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        
        expected = ['starchivos', 'stlogchat', 'stticket']
        found = [t[0] for t in tables]
        
        print(f"[OK] Encontradas {len(tables)} tabla(s):")
        for table in found:
            status = "[OK]" if table in expected else "[WARNING]"
            print(f"   {status} {table}")
        
        missing = set(expected) - set(found)
        if missing:
            print(f"[WARNING] Tablas faltantes: {', '.join(missing)}")
        
        print()
        
        # Test 4: Probar inserción
        print("[INFO] Probando insercion de datos...")
        test_id = f"TKT-TEST-{os.getpid()}"
        
        cur.execute("""
            INSERT INTO soporte_ti.stticket 
            (ticket_id_ticket, ticket_des_ticket, ticket_tip_ticket, 
             ticket_est_ticket, ticket_asu_ticket, ticket_tusua_ticket)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING ticket_cod_ticket
        """, (test_id, 'Test de conexion', 'Software', 'PE', 'Test', 'test_user'))
        
        ticket_id = cur.fetchone()[0]
        conn.commit()
        print(f"[OK] Ticket de prueba insertado (ID: {ticket_id})")
        
        # Limpiar
        cur.execute("DELETE FROM soporte_ti.stticket WHERE ticket_cod_ticket = %s", (ticket_id,))
        conn.commit()
        print("[OK] Ticket de prueba eliminado")
        
        # Test 5: Verificar índices
        cur.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'soporte_ti' 
            ORDER BY indexname
        """)
        indexes = cur.fetchall()
        print(f"[INFO] Indices encontrados: {len(indexes)}")
        
        cur.close()
        conn.close()
        
        print()
        print("="*60)
        print("[SUCCESS] TODOS LOS TESTS PASARON CORRECTAMENTE")
        print("="*60)
        print()
        print("La base de datos esta lista para usar.")
        print()
        return True
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

