"""
Capa de acceso a Google Sheets.

IMPORTANTE sobre concurrencia: la API de Google Sheets no garantiza que
escrituras simultáneas desde varios procesos/hilos no se mezclen o pisen.
Como esta app puede tener hasta 6 personas usando el formulario al mismo
tiempo, usamos un threading.Lock() para que las operaciones de
lectura-luego-escritura (como "generar el próximo ID" o "aprobar un
registro") sean atómicas dentro de este proceso. Como además corremos
todo en un solo proceso Uvicorn (sin múltiples workers), este lock es
suficiente para evitar condiciones de carrera.
"""
import threading
import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

import config

# Lock global: cualquier operación que lea-y-luego-escriba en Sheets
# debe pedir este lock primero, para que dos usuarios no generen el
# mismo ID o no choquen al aprobar/anular al mismo tiempo.
_sheets_lock = threading.Lock()

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_cliente = None
_planilla = None


def _conectar():
    """Crea (una sola vez) la conexión autenticada con Google Sheets."""
    global _cliente, _planilla
    if _planilla is not None:
        return _planilla
    credenciales = Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_PATH, scopes=_SCOPES
    )
    _cliente = gspread.authorize(credenciales)
    _planilla = _cliente.open_by_key(config.SPREADSHEET_ID)
    return _planilla


def _hoja_diagnosticos():
    return _conectar().worksheet(config.SHEET_DIAGNOSTICOS)


def _hoja_administradores():
    return _conectar().worksheet(config.SHEET_ADMINISTRADORES)


def _hoja_historial_reparaciones():
    return _conectar().worksheet(config.SHEET_HISTORIAL_REPARACIONES)


# Encabezados exactos esperados en la pestaña "Diagnosticos"
COLUMNAS_DIAGNOSTICOS = [
    "ID", "FECHA_HORA", "PLATAFORMA", "CONTENEDOR", "RACK", "FILA", "COLUMNA",
    "DIAGNOSTICO", "IP", "SN_DIGITAL", "SN_FISICA", "MAC", "MODELO",
    "TIPO_PIEZA", "PSU_SN", "CHAIN_0", "CHAIN_1", "CHAIN_2", "FUGA",
    "ESTADO", "SUPERVISOR", "OBSERVACION", "APROBADO", "APROBADO_POR",
    "FECHA_APROBACION", "ANULADO",
]


def _generar_id_unico(hoja) -> str:
    """
    Genera un ID con formato DX-YYYYMMDD-NNN, donde NNN es un correlativo
    de 3 dígitos que se reinicia cada día. Debe llamarse SIEMPRE dentro
    del lock para evitar que dos usuarios generen el mismo ID.
    """
    hoy = datetime.date.today().strftime("%Y%m%d")
    prefijo = f"DX-{hoy}-"
    valores_id = hoja.col_values(1)  # Columna A completa = IDs existentes
    correlativos_hoy = [
        int(v.split("-")[-1])
        for v in valores_id
        if v.startswith(prefijo) and v.split("-")[-1].isdigit()
    ]
    siguiente = max(correlativos_hoy, default=0) + 1
    return f"{prefijo}{siguiente:03d}"


def crear_diagnostico(datos: dict) -> str:
    """
    Inserta una nueva fila en la hoja Diagnosticos.
    Devuelve el ID generado.
    """
    with _sheets_lock:
        hoja = _hoja_diagnosticos()
        nuevo_id = _generar_id_unico(hoja)
        fecha_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        fila = []
        for columna in COLUMNAS_DIAGNOSTICOS:
            if columna == "ID":
                fila.append(nuevo_id)
            elif columna == "FECHA_HORA":
                fila.append(fecha_hora)
            elif columna == "APROBADO":
                fila.append("NO")
            elif columna == "APROBADO_POR":
                fila.append("")
            elif columna == "FECHA_APROBACION":
                fila.append("")
            elif columna == "ANULADO":
                fila.append("NO")
            else:
                fila.append(str(datos.get(columna, "") or ""))

        hoja.append_row(fila, value_input_option="USER_ENTERED")
        return nuevo_id


def _todas_las_filas() -> list:
    """
    Devuelve todas las filas de Diagnosticos como lista de diccionarios.

    No usamos expected_headers de gspread porque es demasiado estricto:
    un solo espacio invisible al final de un encabezado en la planilla
    (algo fácil de tipear sin querer) hace que falle toda la lectura.
    En su lugar, leemos los encabezados reales, los normalizamos
    (strip + mayúsculas) y armamos los diccionarios nosotros mismos.
    """
    hoja = _hoja_diagnosticos()
    todos_los_valores = hoja.get_all_values()
    if not todos_los_valores:
        return []

    encabezados_crudos = todos_los_valores[0]
    encabezados = [h.strip().upper() for h in encabezados_crudos]
    filas_de_datos = todos_los_valores[1:]

    registros = []
    for fila in filas_de_datos:
        # Si la fila tiene menos celdas que encabezados (columna vacía al final
        # en Sheets), completamos con "" para no perder el resto de la fila.
        fila_completa = fila + [""] * (len(encabezados) - len(fila))
        registro = dict(zip(encabezados, fila_completa))
        registros.append(registro)
    return registros


def listar_diagnosticos(solo_pendientes: bool = False) -> list:
    filas = _todas_las_filas()
    if solo_pendientes:
        filas = [f for f in filas if str(f.get("APROBADO", "")).upper() == "NO"
                 and str(f.get("ANULADO", "")).upper() != "SI"]

    # Enriquecemos cada fila con el historial de la SN física, para que el
    # admin vea en el Registro si la máquina ya tuvo piezas cambiadas y/o
    # si ya fue reparada antes, con la fecha de cada cosa por separado.
    for fila in filas:
        sn_fisica = fila.get("SN_FISICA", "")
        historial = obtener_historial_por_sn(sn_fisica)
        fila["FECHA_PIEZAS_CAMBIADAS"] = historial["FECHA_PIEZAS_CAMBIADAS"]
        fila["FECHA_REPARACION"] = historial["FECHA_REPARACION"]

    return filas


def contar_pendientes_por_supervisor() -> dict:
    """
    Devuelve {nombre_supervisor: cantidad_pendiente} para mostrar en la
    pantalla principal cuánto le falta aprobar a cada supervisor.
    """
    pendientes = listar_diagnosticos(solo_pendientes=True)
    conteo = {}
    for fila in pendientes:
        supervisor = fila.get("SUPERVISOR", "Desconocido")
        conteo[supervisor] = conteo.get(supervisor, 0) + 1
    return conteo


def _encontrar_fila_por_id(hoja, diagnostico_id: str) -> Optional[int]:
    """Devuelve el número de fila (1-indexed, incluye encabezado) o None."""
    columna_ids = hoja.col_values(1)
    for indice, valor in enumerate(columna_ids, start=1):
        if valor == diagnostico_id:
            return indice
    return None


def aprobar_diagnostico(diagnostico_id: str, admin_nombre: str) -> bool:
    with _sheets_lock:
        hoja = _hoja_diagnosticos()
        fila_numero = _encontrar_fila_por_id(hoja, diagnostico_id)
        if fila_numero is None:
            return False
        col_aprobado = COLUMNAS_DIAGNOSTICOS.index("APROBADO") + 1
        col_aprobado_por = COLUMNAS_DIAGNOSTICOS.index("APROBADO_POR") + 1
        col_fecha_aprobacion = COLUMNAS_DIAGNOSTICOS.index("FECHA_APROBACION") + 1
        fecha_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hoja.update_cell(fila_numero, col_aprobado, "SI")
        hoja.update_cell(fila_numero, col_aprobado_por, admin_nombre)
        hoja.update_cell(fila_numero, col_fecha_aprobacion, fecha_hora)
        return True


def anular_diagnostico(diagnostico_id: str, admin_nombre: str, motivo: str = "") -> bool:
    with _sheets_lock:
        hoja = _hoja_diagnosticos()
        fila_numero = _encontrar_fila_por_id(hoja, diagnostico_id)
        if fila_numero is None:
            return False
        col_anulado = COLUMNAS_DIAGNOSTICOS.index("ANULADO") + 1
        col_observacion = COLUMNAS_DIAGNOSTICOS.index("OBSERVACION") + 1
        hoja.update_cell(fila_numero, col_anulado, "SI")
        if motivo:
            valor_actual = hoja.cell(fila_numero, col_observacion).value or ""
            nueva_obs = f"{valor_actual} [ANULADO por {admin_nombre}: {motivo}]".strip()
            hoja.update_cell(fila_numero, col_observacion, nueva_obs)
        return True


# ---------------------------------------------------------------------------
# Administradores
# ---------------------------------------------------------------------------

def obtener_admin_por_usuario(usuario: str) -> Optional[dict]:
    hoja = _hoja_administradores()
    registros = hoja.get_all_records()
    for registro in registros:
        if str(registro.get("USUARIO", "")).strip().lower() == usuario.strip().lower():
            return registro
    return None


# ---------------------------------------------------------------------------
# Historial de reparaciones
#
# La hoja "Historial_Reparaciones" vive dentro de la misma planilla
# BD_Diagnosticos, y es alimentada por el propio usuario (vía fórmulas de
# Google Sheets) combinando datos de las planillas "Piezas Cambiadas" y
# "Reparados". Acá solo la LEEMOS: 3 columnas —
#   SN_FISICA, FECHA_PIEZAS_CAMBIADAS, FECHA_REPARACION
# (fechas en formato DD/MM/AAAA) — una fila por SN, cada fecha ya
# calculada de antemano como la más reciente de su tipo. Cualquiera de
# las dos fechas puede faltar de forma independiente (ej: una SN puede
# tener cambio de pieza registrado pero ninguna reparación, o viceversa).
#
# Cacheamos el resultado un par de minutos en memoria: este historial
# cambia con poca frecuencia, y así evitamos pedirle a la API de Sheets
# la hoja completa cada vez que un admin abre el Registro de diagnósticos.
# ---------------------------------------------------------------------------
_CACHE_HISTORIAL_SEGUNDOS = 120
_cache_historial = {"datos": None, "leido_en": 0.0}
_cache_historial_lock = threading.Lock()


def _leer_historial_reparaciones() -> dict:
    """
    Devuelve un diccionario:
        {SN_FISICA: {"FECHA_PIEZAS_CAMBIADAS": str|None, "FECHA_REPARACION": str|None}}
    a partir de la hoja Historial_Reparaciones, usando un caché en memoria
    de _CACHE_HISTORIAL_SEGUNDOS para no golpear la API en cada consulta.
    """
    import time

    with _cache_historial_lock:
        ahora = time.time()
        si_cache_vigente = (
            _cache_historial["datos"] is not None
            and (ahora - _cache_historial["leido_en"]) < _CACHE_HISTORIAL_SEGUNDOS
        )
        if si_cache_vigente:
            return _cache_historial["datos"]

        hoja = _hoja_historial_reparaciones()
        valores = hoja.get_all_values()
        mapa = {}
        if valores:
            encabezados = [h.strip().upper() for h in valores[0]]
            try:
                idx_sn = encabezados.index("SN_FISICA")
                idx_piezas = encabezados.index("FECHA_PIEZAS_CAMBIADAS")
                idx_reparacion = encabezados.index("FECHA_REPARACION")
            except ValueError:
                # Encabezados inesperados: devolvemos vacío en lugar de
                # romper el Registro completo por un problema en esta hoja.
                _cache_historial["datos"] = {}
                _cache_historial["leido_en"] = ahora
                return {}

            indice_maximo = max(idx_sn, idx_piezas, idx_reparacion)
            for fila in valores[1:]:
                if len(fila) <= indice_maximo:
                    # completamos celdas faltantes al final de la fila con ""
                    fila = fila + [""] * (indice_maximo + 1 - len(fila))
                sn = fila[idx_sn].strip().upper()
                if not sn:
                    continue
                fecha_piezas = fila[idx_piezas].strip() or None
                fecha_reparacion = fila[idx_reparacion].strip() or None
                mapa[sn] = {
                    "FECHA_PIEZAS_CAMBIADAS": fecha_piezas,
                    "FECHA_REPARACION": fecha_reparacion,
                }

        _cache_historial["datos"] = mapa
        _cache_historial["leido_en"] = ahora
        return mapa


def obtener_historial_por_sn(sn_fisica: str) -> dict:
    """
    Busca la SN física (exacta, sin espacios, sin distinguir mayúsculas)
    en el historial de reparaciones. Devuelve siempre un diccionario con
    ambas claves, aunque no haya datos:
        {"FECHA_PIEZAS_CAMBIADAS": str|None, "FECHA_REPARACION": str|None}
    """
    vacio = {"FECHA_PIEZAS_CAMBIADAS": None, "FECHA_REPARACION": None}
    if not sn_fisica:
        return vacio
    mapa = _leer_historial_reparaciones()
    return mapa.get(sn_fisica.strip().upper(), vacio)
