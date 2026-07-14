"""
Autenticación de administradores.

Las contraseñas se guardan en la hoja "Administradores" como un HASH
(bcrypt), nunca en texto plano. Este módulo incluye también una utilidad
de línea de comandos para generar el hash de una contraseña nueva, que
vas a usar para crear tus primeros usuarios admin directamente en la
planilla de Google Sheets.

Las sesiones se manejan con un token aleatorio simple guardado en memoria
(diccionario). Esto es suficiente para un equipo pequeño en red local;
si el servidor se reinicia, los admins deben volver a iniciar sesión.
"""
import secrets
import time
import threading

import bcrypt

import sheets_service

# token -> {"usuario": str, "nombre": str, "creado": timestamp}
_sesiones = {}
_sesiones_lock = threading.Lock()

DURACION_SESION_SEGUNDOS = 8 * 60 * 60  # 8 horas


def hashear_password(password_en_texto_plano: str) -> str:
    """Genera el hash bcrypt para guardar en la planilla."""
    return bcrypt.hashpw(password_en_texto_plano.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verificar_password(password_en_texto_plano: str, hash_guardado: str) -> bool:
    try:
        return bcrypt.checkpw(password_en_texto_plano.encode("utf-8"), hash_guardado.encode("utf-8"))
    except (ValueError, AttributeError):
        return False


def login(usuario: str, password: str):
    """
    Intenta autenticar a un administrador.
    Devuelve (token, nombre) si es correcto, o (None, None) si falla.
    """
    admin = sheets_service.obtener_admin_por_usuario(usuario)
    if not admin:
        return None, None
    hash_guardado = admin.get("PASSWORD_HASH", "")
    if not _verificar_password(password, hash_guardado):
        return None, None

    token = secrets.token_hex(32)
    nombre = admin.get("NOMBRE", usuario)
    with _sesiones_lock:
        _sesiones[token] = {"usuario": usuario, "nombre": nombre, "creado": time.time()}
    return token, nombre


def validar_token(token: str):
    """Devuelve el nombre del admin si el token es válido y no expiró, o None."""
    with _sesiones_lock:
        sesion = _sesiones.get(token)
        if not sesion:
            return None
        if time.time() - sesion["creado"] > DURACION_SESION_SEGUNDOS:
            del _sesiones[token]
            return None
        return sesion["nombre"]


def cerrar_sesion(token: str):
    with _sesiones_lock:
        _sesiones.pop(token, None)


if __name__ == "__main__":
    # Utilidad de consola: genera un hash para pegar en la columna
    # PASSWORD_HASH de la hoja "Administradores".
    # Uso: python auth.py
    import getpass
    print("=== Generador de hash de contraseña para administradores ===")
    clave = getpass.getpass("Escribí la contraseña a hashear: ")
    print("\nCopiá este hash en la columna PASSWORD_HASH de la planilla:\n")
    print(hashear_password(clave))
