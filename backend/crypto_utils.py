from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# --- IMPORTANTE: Estas son las llaves de tu código PowerBuilder ---
# Deben ser exactamente de 16 bytes.
KEY = b"prue Key12345678"  # b'' indica que es un string de bytes
IV = b"prue IV 12345678"   # Initialization Vector

# El encoding 'latin-1' es el equivalente más cercano a EncodingANSI! de PowerBuilder
ENCODING = 'latin-1'

def decrypt_password(encrypted_blob: bytes) -> str:
    """
    Desencripta un blob de bytes desde la base de datos Informix.
    Replica la lógica SymmetricDecrypt de PowerBuilder.
    """
    if not encrypted_blob:
        return ""
        
    try:
        # 1. Crear el objeto de cifrado con la misma configuración que PowerBuilder
        cipher = AES.new(KEY, AES.MODE_CBC, IV)
        
        # 2. Desencriptar el blob de datos
        decrypted_padded_data = cipher.decrypt(encrypted_blob)
        
        # 3. Quitar el "relleno" (padding) que se añadió durante la encriptación
        decrypted_data = unpad(decrypted_padded_data, AES.block_size)
        
        # 4. Decodificar los bytes a un string legible
        return decrypted_data.decode(ENCODING)
    except (ValueError, KeyError) as e:
        # Este error suele ocurrir si la llave es incorrecta o los datos están corruptos
        print(f"Error al desencriptar la contraseña: {e}. ¿La llave y el IV son correctos?")
        return "ErrorDeEncriptacion"

# --- Opcional: Función para encriptar (útil para pruebas) ---
def encrypt_password(plain_text_password: str) -> bytes:
    """
    Encripta una contraseña en texto plano.
    Replica la lógica SymmetricEncrypt de PowerBuilder.
    """
    try:
        cipher = AES.new(KEY, AES.MODE_CBC, IV)
        
        # 1. Convertir el texto a bytes y añadir padding
        data_to_encrypt = pad(plain_text_password.encode(ENCODING), AES.block_size)
        
        # 2. Encriptar
        encrypted_data = cipher.encrypt(data_to_encrypt)
        return encrypted_data
    except Exception as e:
        print(f"Error al encriptar: {e}")
        return b""
