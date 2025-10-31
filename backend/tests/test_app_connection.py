#!/usr/bin/env python3
"""
Test de conexion usando las mismas funciones de app.py
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import get_postgres_connection
from dotenv import load_dotenv

load_dotenv()

def test_app_db_connection():
    """Prueba la conexion usando la funcion de app.py"""
    print("="*60)
    print("TEST DE CONEXION DESDE APP.PY")
    print("="*60)
    print()
    
    print("[INFO] Probando get_postgres_connection()...")
    
    conn = get_postgres_connection()
    
    if not conn:
        print("[ERROR] No se pudo conectar a PostgreSQL")
        print("Verifica que el archivo .env este configurado correctamente")
        return False
    
    print("[OK] Conexion establecida exitosamente")
    
    try:
        # Probar consulta simple
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"[OK] PostgreSQL version: {version.split(',')[0]}")
            
            # Verificar que las tablas existan
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'soporte_ti'
                ORDER BY table_name
            """)
            tables = cur.fetchall()
            
            print(f"[OK] Tablas disponibles: {len(tables)}")
            for table in tables:
                print(f"   - {table[0]}")
            
            # Contar tickets existentes
            cur.execute("SELECT COUNT(*) FROM soporte_ti.stticket")
            count = cur.fetchone()[0]
            print(f"[INFO] Tickets en la base de datos: {count}")
            
            # Contar archivos
            cur.execute("SELECT COUNT(*) FROM soporte_ti.starchivos")
            count = cur.fetchone()[0]
            print(f"[INFO] Archivos adjuntos: {count}")
            
            # Contar logs
            cur.execute("SELECT COUNT(*) FROM soporte_ti.stlogchat")
            count = cur.fetchone()[0]
            print(f"[INFO] Logs de chat: {count}")
        
        conn.close()
        
        print()
        print("="*60)
        print("[SUCCESS] LA APP PUEDE CONECTARSE AL RDS")
        print("="*60)
        print()
        print("Tu aplicacion Flask esta lista para usar el RDS!")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error al ejecutar consultas: {e}")
        conn.close()
        return False

if __name__ == "__main__":
    success = test_app_db_connection()
    sys.exit(0 if success else 1)

