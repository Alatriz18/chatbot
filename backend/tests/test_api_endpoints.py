#!/usr/bin/env python3
"""
Test de endpoints de la API Flask
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_endpoint(name, url, method="GET", data=None):
    """Prueba un endpoint y muestra el resultado"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{url}", timeout=5)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{url}", json=data, timeout=5)
        
        status_icon = "[OK]" if response.status_code == 200 else "[ERROR]"
        print(f"{status_icon} {name}")
        print(f"    URL: {url}")
        print(f"    Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if isinstance(result, list):
                    print(f"    Resultado: {len(result)} item(s)")
                elif isinstance(result, dict):
                    print(f"    Resultado: {list(result.keys())}")
            except:
                print(f"    Resultado: {response.text[:100]}")
        else:
            print(f"    Error: {response.text[:200]}")
        
        print()
        return response.status_code == 200
        
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] {name}")
        print(f"    No se pudo conectar a {BASE_URL}")
        print(f"    Asegurate de que el servidor Flask este corriendo")
        print()
        return False
    except Exception as e:
        print(f"[ERROR] {name}")
        print(f"    Error: {str(e)}")
        print()
        return False

def main():
    print("="*60)
    print("TEST DE ENDPOINTS DE LA API")
    print("="*60)
    print()
    
    tests = []
    
    # Test 1: Página principal
    tests.append(test_endpoint(
        "Pagina principal",
        "/",
        "GET"
    ))
    
    # Test 2: Obtener todos los tickets
    tests.append(test_endpoint(
        "GET /api/admin/tickets",
        "/api/admin/tickets",
        "GET"
    ))
    
    # Test 3: Obtener administradores (usa Informix)
    tests.append(test_endpoint(
        "GET /api/admins (Informix)",
        "/api/admins",
        "GET"
    ))
    
    # Test 4: Crear un ticket de prueba
    test_data = {
        "context": {
            "problemDescription": "Test desde script de prueba",
            "categoryKey": "software",
            "subcategoryKey": "Test automatizado",
            "finalOptionsTried": []
        },
        "user": {
            "username": "test_user",
            "user_code": 999
        },
        "preferred_admin": "none"
    }
    
    tests.append(test_endpoint(
        "POST /api/tickets (Crear ticket)",
        "/api/tickets",
        "POST",
        test_data
    ))
    
    # Resumen
    print("="*60)
    passed = sum(tests)
    total = len(tests)
    
    if passed == total:
        print(f"[SUCCESS] Todos los tests pasaron ({passed}/{total})")
        print()
        print("Tu aplicacion Flask esta funcionando correctamente con RDS!")
    else:
        print(f"[WARNING] {passed}/{total} tests pasaron")
        print()
        print("Algunos endpoints pueden requerir configuracion adicional")
    
    print("="*60)

if __name__ == "__main__":
    main()

