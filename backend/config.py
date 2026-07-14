"""
Configuración general de la aplicación.
Carga las variables desde el archivo .env
"""
import os
import base64
import json
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Raíz del proyecto = una carpeta arriba de "backend" (donde está este archivo)
BASE_DIR = Path(__file__).resolve().parent.parent

# Buscamos el .env explícitamente en la raíz del proyecto, para que no
# importe desde qué carpeta se ejecute "uvicorn main:app".
load_dotenv(BASE_DIR / ".env")

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# Manejo de credenciales: soportar base64 (production en Replit) o archivo (local)
_creds_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
if _creds_b64:
    # Production: credenciales en base64 como env var
    try:
        creds_json_str = base64.b64decode(_creds_b64).decode("utf-8")
        creds_dict = json.loads(creds_json_str)
        # Guardar en archivo temporal para que gspread pueda leer
        _temp_creds = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(creds_dict, _temp_creds)
        _temp_creds.close()
        GOOGLE_CREDENTIALS_PATH = _temp_creds.name
    except Exception as e:
        raise RuntimeError(f"Error al decodificar GOOGLE_CREDENTIALS_B64: {e}")
else:
    # Local development: usar archivo tradicional
    _ruta_credenciales = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/service_account.json")
    GOOGLE_CREDENTIALS_PATH = str(BASE_DIR / _ruta_credenciales)

APP_PORT = int(os.getenv("APP_PORT", 8000))
SECRET_KEY = os.getenv("SECRET_KEY", "clave-temporal-cambiar")

# Nombres de las pestañas dentro de la planilla
SHEET_DIAGNOSTICOS = "Diagnosticos"
SHEET_ADMINISTRADORES = "Administradores"
SHEET_HISTORIAL_REPARACIONES = "Historial_Reparaciones"

if not SPREADSHEET_ID:
    raise RuntimeError(
        "Falta SPREADSHEET_ID en el archivo .env. "
        "Copiá .env.example como .env y completá los valores."
    )
