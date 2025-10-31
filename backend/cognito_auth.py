"""
Middleware de Autenticación con AWS Cognito
Valida tokens JWT de Cognito y proporciona información del usuario
"""

import jwt
import requests
import os
import logging
from functools import wraps
from flask import request, jsonify
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Configuración
COGNITO_REGION = os.getenv('COGNITO_REGION', 'us-east-1')
COGNITO_USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID', 'us-east-1_hERvQ0wWv')
COGNITO_JWKS_URL = f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json'
COGNITO_ISSUER = f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}'

# Cache para las claves públicas de Cognito
_jwks_cache: Optional[Dict[str, Any]] = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_cognito_public_keys() -> Dict[str, Any]:
    """
    Obtiene las claves públicas de Cognito para validar tokens JWT
    """
    global _jwks_cache
    
    if _jwks_cache is not None:
        return _jwks_cache
    
    try:
        response = requests.get(COGNITO_JWKS_URL, timeout=10)
        response.raise_for_status()
        _jwks_cache = response.json()
        logger.info("Claves públicas de Cognito obtenidas exitosamente")
        return _jwks_cache
    except Exception as e:
        logger.error(f"Error obteniendo claves públicas de Cognito: {e}")
        raise Exception("No se pudieron obtener las claves de Cognito")


def get_public_key_for_token(token: str) -> str:
    """
    Obtiene la clave pública específica para un token JWT
    """
    try:
        # Decodificar el header del token sin verificar (solo para obtener el 'kid')
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        if not kid:
            raise Exception("Token no tiene 'kid' en el header")
        
        # Obtener las claves públicas
        jwks = get_cognito_public_keys()
        
        # Buscar la clave que coincida con el 'kid'
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                # Convertir la clave JWK a formato PEM
                from jwt.algorithms import RSAAlgorithm
                public_key = RSAAlgorithm.from_jwk(key)
                return public_key
        
        raise Exception(f"No se encontró clave pública para kid: {kid}")
        
    except Exception as e:
        logger.error(f"Error obteniendo clave pública: {e}")
        raise


def verify_cognito_token(token: str) -> Dict[str, Any]:
    """
    Verifica y decodifica un token de Cognito
    
    Args:
        token: Token JWT de Cognito
        
    Returns:
        Payload del token (claims)
        
    Raises:
        Exception: Si el token es inválido
    """
    try:
        # Obtener la clave pública para este token
        public_key = get_public_key_for_token(token)
        
        # Verificar y decodificar el token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            issuer=COGNITO_ISSUER,
            options={
                'verify_exp': True,
                'verify_iss': True,
                'verify_aud': False  # Cognito access tokens no tienen 'aud'
            }
        )
        
        logger.info(f"Token verificado exitosamente para usuario: {payload.get('username', 'unknown')}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token expirado")
        raise Exception("Token expirado")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token inválido: {e}")
        raise Exception("Token inválido")
    except Exception as e:
        logger.error(f"Error verificando token: {e}")
        raise Exception(f"Error al verificar token: {str(e)}")


def extract_token_from_header() -> Optional[str]:
    """
    Extrae el token del header Authorization
    
    Returns:
        Token JWT o None si no está presente
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header:
        return None
    
    # El formato debe ser: "Bearer <token>"
    parts = auth_header.split()
    
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]


def get_user_from_token(token_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae información del usuario del payload del token
    
    Args:
        token_payload: Payload decodificado del token JWT
        
    Returns:
        Diccionario con información del usuario
    """
    return {
        'sub': token_payload.get('sub'),  # UUID del usuario en Cognito
        'username': token_payload.get('username'),
        'email': token_payload.get('email'),
        'groups': token_payload.get('cognito:groups', []),
        'token_use': token_payload.get('token_use'),  # 'access' o 'id'
        'auth_time': token_payload.get('auth_time'),
        'exp': token_payload.get('exp')
    }


# DECORADORES PARA PROTEGER ENDPOINTS

def require_auth(f):
    """
    Decorador para requerir autenticación en un endpoint
    
    Uso:
        @app.route('/api/protected')
        @require_auth
        def protected_route():
            user = request.user
            return jsonify({'message': f'Hola {user["username"]}'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Extraer token
            token = extract_token_from_header()
            
            if not token:
                return jsonify({
                    'error': 'Token de autenticación requerido',
                    'message': 'Proporciona un token en el header Authorization'
                }), 401
            
            # Verificar token
            token_payload = verify_cognito_token(token)
            
            # Agregar información del usuario al request
            request.user = get_user_from_token(token_payload)
            request.token_payload = token_payload
            
            # Continuar con la función original
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            return jsonify({
                'error': 'Token inválido o expirado',
                'message': str(e)
            }), 403
    
    return decorated_function


def require_admin(f):
    """
    Decorador para requerir que el usuario sea administrador
    
    Uso:
        @app.route('/api/admin/users')
        @require_admin
        def admin_route():
            return jsonify({'message': 'Solo admins pueden ver esto'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Primero verificar autenticación
            token = extract_token_from_header()
            
            if not token:
                return jsonify({'error': 'Token de autenticación requerido'}), 401
            
            token_payload = verify_cognito_token(token)
            user = get_user_from_token(token_payload)
            
            # Verificar si es admin
            groups = user.get('groups', [])
            is_admin = 'admin' in groups or 'Administradores' in groups
            
            if not is_admin:
                logger.warning(f"Acceso denegado para usuario: {user.get('username')}")
                return jsonify({
                    'error': 'Acceso denegado',
                    'message': 'Se requieren permisos de administrador'
                }), 403
            
            # Agregar información del usuario al request
            request.user = user
            request.token_payload = token_payload
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error en verificación de admin: {e}")
            return jsonify({'error': 'Token inválido o expirado'}), 403
    
    return decorated_function


def optional_auth(f):
    """
    Decorador para hacer la autenticación opcional
    Si hay token, se valida y se agrega al request
    Si no hay token, continúa sin autenticación
    
    Uso:
        @app.route('/api/public-or-private')
        @optional_auth
        def mixed_route():
            user = getattr(request, 'user', None)
            if user:
                return jsonify({'message': f'Hola {user["username"]}'})
            else:
                return jsonify({'message': 'Hola invitado'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = extract_token_from_header()
            
            if token:
                try:
                    token_payload = verify_cognito_token(token)
                    request.user = get_user_from_token(token_payload)
                    request.token_payload = token_payload
                except:
                    # Si el token es inválido, continuar sin autenticación
                    pass
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error en autenticación opcional: {e}")
            return f(*args, **kwargs)
    
    return decorated_function


# Función helper para obtener el usuario actual
def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Obtiene el usuario actual del request
    
    Returns:
        Diccionario con información del usuario o None si no está autenticado
    """
    return getattr(request, 'user', None)


# Función helper para verificar si el usuario está autenticado
def is_authenticated() -> bool:
    """
    Verifica si hay un usuario autenticado en el request actual
    
    Returns:
        True si hay usuario autenticado, False si no
    """
    return hasattr(request, 'user') and request.user is not None

