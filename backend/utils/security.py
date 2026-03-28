import os
from cryptography.fernet import Fernet

# En producción, esta llave debe venir de una variable de entorno segura
# Si no está definida, se usa una por defecto para el MVP (¡NO HACER EN PRODUCCIÓN REAL!)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "7T_l_Ym70_jW9NnX1XFp_7z5vE_oG8g_O7S8h_J5m0=")

def obtener_fernet():
    return Fernet(ENCRYPTION_KEY.encode())

def encrypt_data(data: str) -> str:
    """Encriptar una cadena de texto"""
    if not data:
        return ""
    f = obtener_fernet()
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Desencriptar una cadena de texto"""
    if not encrypted_data:
        return ""
    try:
        f = obtener_fernet()
        return f.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        print(f"Error descifrando datos: {e}")
        return ""
