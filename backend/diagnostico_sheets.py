"""
Script de diagnóstico AISLADO para depurar la conexión con Google Sheets,
sin pasar por FastAPI ni por el resto de la app.

Uso:
    cd backend
    python diagnostico_sheets.py

Va mostrando cada paso y dónde falla exactamente, con toda la info posible.
"""
import os
import sys
from pathlib import Path

print("=" * 70)
print("DIAGNÓSTICO DE CONEXIÓN A GOOGLE SHEETS")
print("=" * 70)

# --- Paso 1: ubicar y leer el .env ---
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
print(f"\n[1] Buscando .env en: {env_path}")
print(f"    ¿Existe?: {env_path.exists()}")

from dotenv import load_dotenv
load_dotenv(env_path)

spreadsheet_id = os.getenv("SPREADSHEET_ID")
creds_path_raw = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/service_account.json")
creds_path = str(BASE_DIR / creds_path_raw)

print(f"\n[2] SPREADSHEET_ID leído del .env:")
print(f"    Valor: '{spreadsheet_id}'")
print(f"    Longitud: {len(spreadsheet_id) if spreadsheet_id else 0}")
if spreadsheet_id:
    print(f"    Repr (para detectar espacios ocultos): {repr(spreadsheet_id)}")

print(f"\n[3] Ruta de credenciales calculada:")
print(f"    {creds_path}")
print(f"    ¿Existe el archivo?: {Path(creds_path).exists()}")

# --- Paso 2: leer el archivo de credenciales y mostrar datos clave ---
import json
print(f"\n[4] Contenido relevante del archivo de credenciales:")
try:
    with open(creds_path, "r", encoding="utf-8") as f:
        info = json.load(f)
    print(f"    project_id: {info.get('project_id')}")
    print(f"    client_email: {info.get('client_email')}")
    print(f"    type: {info.get('type')}")
except Exception as e:
    print(f"    ERROR leyendo el archivo: {e}")
    sys.exit(1)

# --- Paso 3: autenticar ---
print(f"\n[5] Autenticando con Google...")
from google.oauth2.service_account import Credentials
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
try:
    credenciales = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    print("    Autenticación local OK (el archivo de credenciales es válido).")
except Exception as e:
    print(f"    ERROR al autenticar: {e}")
    sys.exit(1)

# --- Paso 4: conectar con gspread y listar TODAS las planillas visibles ---
import gspread
print(f"\n[6] Conectando con gspread...")
try:
    cliente = gspread.authorize(credenciales)
    print("    Conexión OK.")
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

print(f"\n[7] Listando TODAS las planillas a las que esta cuenta de servicio tiene acceso:")
try:
    planillas = cliente.openall()
    if not planillas:
        print("    -> NINGUNA. La cuenta de servicio no tiene acceso a ninguna planilla.")
        print("    -> Esto confirma que el problema es de PERMISOS, no del ID.")
    else:
        for p in planillas:
            print(f"    - Título: '{p.title}'  |  ID: {p.id}")
            if p.id == spreadsheet_id:
                print(f"      *** ESTE es el ID que tenés en tu .env -> coincide ***")
except Exception as e:
    print(f"    ERROR al listar: {e}")

# --- Paso 5: intentar abrir la planilla específica por ID ---
print(f"\n[8] Intentando abrir la planilla específica por SPREADSHEET_ID...")
try:
    planilla = cliente.open_by_key(spreadsheet_id)
    print(f"    ¡ÉXITO! Título de la planilla: '{planilla.title}'")
    print(f"\n    Pestañas (hojas) dentro de esta planilla:")
    for hoja in planilla.worksheets():
        print(f"      - '{hoja.title}'")
except Exception as e:
    print(f"    ERROR: {type(e).__name__}: {e}")

print("\n" + "=" * 70)
print("FIN DEL DIAGNÓSTICO")
print("=" * 70)
