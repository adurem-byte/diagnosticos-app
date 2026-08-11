"""
Modelos de datos (Pydantic) y catálogos de opciones para los menús desplegables.
"""
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Catálogos para los <select> del frontend
# ---------------------------------------------------------------------------

PLATAFORMAS = [f"PLATAFORMA {i}" for i in range(1, 7)]

RACKS = ["A", "B"]

TIPOS_PIEZA = [
    "APW111721C",
]

# MODELO ahora es un selector fijo de 3 opciones (no texto libre).
# Debe coincidir con el 7° carácter de SN_FISICA: B->338T, C->358T, D->395T.
MODELO_OPCIONES = ["338T", "358T", "395T"]

FUGA_OPCIONES = ["INTERNO", "MANGUERITA", "CONJ. DE DIST."]

ESTADO_OPCIONES = ["Desconectado", "Desconectado y log descargado"]

# Semilla de diagnosticadores: solo se usa para llenar la pestaña
# "Diagnosticadores" la primera vez. A partir de ahí la lista vive en la
# planilla y se administra desde el panel de admin, así que editar esto no
# cambia nada en una instalación ya andando.
SUPERVISORES = [
    "Daniel Bruno",
    "Alexis Chavez",
    "Fabian Duarte",
    "José Barreto",
    "Carlos Rojas",
    "Jesús González",
    "Abel Duré",
    "Matias Aguilera",
    "Matias Romero",
]


def contenedores_por_plataforma(plataforma: str) -> list:
    from validators import RANGOS_CONTENEDOR
    rango = RANGOS_CONTENEDOR.get(plataforma)
    if not rango:
        return []
    minimo, maximo = rango
    return list(range(minimo, maximo + 1))


# ---------------------------------------------------------------------------
# Modelo del formulario de diagnóstico
# ---------------------------------------------------------------------------

class DiagnosticoInput(BaseModel):
    """
    Todos los campos llegan como string opcional. La razón es que distintos
    diagnósticos requieren distintos campos, así que la validación de
    "obligatorio/opcional/no necesario" se hace aparte (diagnostics_rules.py)
    en lugar de declarar campos fijos requeridos acá.
    """
    PLATAFORMA: Optional[str] = None
    CONTENEDOR: Optional[str] = None
    RACK: Optional[str] = None
    FILA: Optional[str] = None
    COLUMNA: Optional[str] = None
    DIAGNOSTICO: Optional[str] = None
    IP: Optional[str] = None
    SN_DIGITAL: Optional[str] = None
    SN_FISICA: Optional[str] = None
    MAC: Optional[str] = None
    MODELO: Optional[str] = None
    TIPO_PIEZA: Optional[str] = None
    PSU_SN: Optional[str] = None
    CHAIN_0: Optional[str] = None
    CHAIN_1: Optional[str] = None
    CHAIN_2: Optional[str] = None
    FUGA: Optional[str] = None
    ESTADO: Optional[str] = None
    SUPERVISOR: Optional[str] = None
    OBSERVACION: Optional[str] = None


class LoginInput(BaseModel):
    usuario: str
    password: str


class AprobarInput(BaseModel):
    token: str
    diagnostico_id: str


class AnularInput(BaseModel):
    token: str
    diagnostico_id: str
    motivo: Optional[str] = None


class EditarInput(BaseModel):
    """Corrección de un diagnóstico ya registrado, hecha por un admin."""
    token: str
    diagnostico_id: str
    datos: DiagnosticoInput


class DiagnosticadoresInput(BaseModel):
    """Lista completa de diagnosticadores tal como debe quedar guardada."""
    token: str
    nombres: list[str]
