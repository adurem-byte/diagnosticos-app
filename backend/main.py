"""
Punto de entrada de la aplicación. Define todas las rutas de la API
y sirve los archivos del frontend.

Para correr el servidor:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
(durante desarrollo; en producción se quita --reload, ver Paso final)
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import auth
import config
import models
import sheets_service
import validators
from diagnostics_rules import (
    REGLAS_POR_DIAGNOSTICO,
    DIAGNOSTICOS_DISPONIBLES,
    OBLIGATORIO,
    OPCIONAL,
    NO_NECESARIO,
)

app = FastAPI(title="Diagnósticos de Máquinas")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ---------------------------------------------------------------------------
# Rutas de catálogos / configuración para que el frontend arme el formulario
# ---------------------------------------------------------------------------

@app.get("/api/catalogos")
def obtener_catalogos():
    """Todas las listas fijas que necesita el frontend para los <select>."""
    return {
        "plataformas": models.PLATAFORMAS,
        "racks": models.RACKS,
        "diagnosticos": DIAGNOSTICOS_DISPONIBLES,
        "modelo_opciones": models.MODELO_OPCIONES,
        "tipos_pieza": models.TIPOS_PIEZA,
        "fuga_opciones": models.FUGA_OPCIONES,
        "estado_opciones": models.ESTADO_OPCIONES,
        "supervisores": models.SUPERVISORES,
    }


@app.get("/api/contenedores/{plataforma}")
def obtener_contenedores(plataforma: str):
    lista = models.contenedores_por_plataforma(plataforma)
    if not lista:
        raise HTTPException(status_code=404, detail="Plataforma no reconocida.")
    return {"contenedores": lista}


@app.get("/api/reglas/{diagnostico}")
def obtener_reglas_diagnostico(diagnostico: str):
    """Devuelve el mapa {campo: OBLIGATORIO|OPCIONAL|NO_NECESARIO}."""
    reglas = REGLAS_POR_DIAGNOSTICO.get(diagnostico)
    if reglas is None:
        raise HTTPException(status_code=404, detail="Diagnóstico no reconocido.")
    return {"diagnostico": diagnostico, "reglas": reglas}


# ---------------------------------------------------------------------------
# Validación + creación de diagnósticos
# ---------------------------------------------------------------------------

def _validar_formulario(datos: models.DiagnosticoInput) -> list:
    """
    Valida formato y obligatoriedad de TODOS los campos según el
    diagnóstico elegido. Devuelve una lista de mensajes de error
    (vacía si todo está bien).
    """
    errores = []
    diagnostico = (datos.DIAGNOSTICO or "").strip()

    if diagnostico not in REGLAS_POR_DIAGNOSTICO:
        return ["Debe seleccionar un DIAGNÓSTICO válido."]

    reglas = REGLAS_POR_DIAGNOSTICO[diagnostico]
    valores = datos.model_dump()

    for campo, nivel in reglas.items():
        valor = (valores.get(campo) or "").strip()

        if nivel == NO_NECESARIO:
            continue  # no se valida ni se exige

        if nivel == OBLIGATORIO and not valor:
            errores.append(f"El campo {campo.replace('_', ' ')} es obligatorio para el diagnóstico {diagnostico}.")
            continue

        if not valor:
            continue  # OPCIONAL y vacío: no hay nada que validar

        # Si llegamos aquí, hay un valor presente (obligatorio u opcional) -> validar formato
        if campo == "FILA":
            ok, error = validators.validar_fila(valor, (valores.get("RACK") or ""))
        elif campo == "COLUMNA":
            ok, error = validators.validar_columna(valor)
        elif campo == "CONTENEDOR":
            ok, error = validators.validar_contenedor(valor, valores.get("PLATAFORMA", ""))
        elif campo == "IP":
            ok, error = validators.validar_ip(valor)
        elif campo == "SN_DIGITAL":
            ok, error = validators.validar_sn_digital(valor)
        elif campo == "SN_FISICA":
            ok, error = validators.validar_sn_fisica(valor)
        elif campo == "MAC":
            ok, error = validators.validar_mac(valor)
        elif campo == "MODELO":
            ok, error = validators.validar_modelo(valor, valores.get("SN_FISICA", ""))
        elif campo == "PSU_SN":
            ok, error = validators.validar_psu_sn(valor)
        elif campo in ("CHAIN_0", "CHAIN_1", "CHAIN_2"):
            ok, error = validators.validar_chain(valor, campo.replace("_", " "))
        else:
            ok, error = True, None  # campos sin regla de formato (ej: SUPERVISOR, OBSERVACION)

        if not ok:
            errores.append(error)

    # Validar que no haya números de serie duplicados en el mismo formulario
    campos_sn = ["SN_DIGITAL", "SN_FISICA", "PSU_SN", "CHAIN_0", "CHAIN_1", "CHAIN_2"]
    sns_ingresados = []
    for c_sn in campos_sn:
        val_sn = (valores.get(c_sn) or "").strip()
        if val_sn:
            sns_ingresados.append(val_sn.upper())
            
    if len(sns_ingresados) != len(set(sns_ingresados)):
        errores.append("No se permiten números de serie (SN) duplicados en un mismo diagnóstico.")

    return errores


@app.post("/api/diagnosticos")
def crear_diagnostico(datos: models.DiagnosticoInput):
    errores = _validar_formulario(datos)
    if errores:
        # Se devuelve el primer error y la lista completa; el frontend
        # decide si muestra todos o uno por uno como ventana emergente.
        raise HTTPException(status_code=422, detail={"errores": errores})

    nuevo_id = sheets_service.crear_diagnostico(datos.model_dump())
    return {"ok": True, "id": nuevo_id}


@app.get("/api/diagnosticos")
def listar_diagnosticos(solo_pendientes: bool = False):
    return {"diagnosticos": sheets_service.listar_diagnosticos(solo_pendientes=solo_pendientes)}


@app.get("/api/pendientes/resumen")
def resumen_pendientes():
    """
    Para la pantalla principal: cuántos traslados pendientes hay por
    supervisor, para que cualquiera (sin ser admin) vea cuánto falta
    aprobar.
    """
    conteo = sheets_service.contar_pendientes_por_supervisor()
    total = sum(conteo.values())
    return {"total_pendientes": total, "por_supervisor": conteo}


# ---------------------------------------------------------------------------
# Administración (requiere token de sesión válido)
# ---------------------------------------------------------------------------

def _requerir_admin(token: str):
    nombre = auth.validar_token(token)
    if not nombre:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada. Inicie sesión nuevamente.")
    return nombre


@app.post("/api/admin/login")
def admin_login(datos: models.LoginInput):
    token, nombre = auth.login(datos.usuario, datos.password)
    if not token:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    return {"token": token, "nombre": nombre}


@app.post("/api/admin/logout")
def admin_logout(datos: dict):
    auth.cerrar_sesion(datos.get("token", ""))
    return {"ok": True}


@app.post("/api/admin/verificar")
def admin_verificar(datos: dict):
    nombre = _requerir_admin(datos.get("token", ""))
    return {"nombre": nombre}


@app.post("/api/admin/aprobar")
def aprobar(datos: models.AprobarInput):
    nombre_admin = _requerir_admin(datos.token)
    exito = sheets_service.aprobar_diagnostico(datos.diagnostico_id, nombre_admin)
    if not exito:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado.")
    return {"ok": True}


@app.post("/api/admin/anular")
def anular(datos: models.AnularInput):
    nombre_admin = _requerir_admin(datos.token)
    exito = sheets_service.anular_diagnostico(datos.diagnostico_id, nombre_admin, datos.motivo or "")
    if not exito:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado.")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Frontend (archivos estáticos)
# ---------------------------------------------------------------------------

app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")


@app.get("/")
def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))
