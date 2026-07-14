"""
Validadores de formato para cada campo del diagnóstico.

Cada función recibe el valor (string) y devuelve:
    (True, None)         si es válido
    (False, "mensaje")   si no es válido, con el mensaje de error a mostrar

Estas mismas reglas se replican en el frontend (js/app.js) para dar feedback
inmediato al usuario, pero el backend SIEMPRE vuelve a validar antes de
guardar en Sheets — nunca confiamos solo en la validación del navegador.
"""
import re

# Rangos de contenedor según plataforma (regla de negocio)
RANGOS_CONTENEDOR = {
    "PLATAFORMA 1": (1, 12),
    "PLATAFORMA 2": (13, 30),
    "PLATAFORMA 3": (31, 54),
    "PLATAFORMA 4": (55, 78),
    "PLATAFORMA 5": (79, 94),
    "PLATAFORMA 6": (95, 110),
}

# Mapeo del 7mo carácter de SN_FISICA -> texto que debe incluir el MODELO
MODELO_POR_CARACTER = {
    "B": "338T",
    "C": "358T",
    "D": "395T",
}


def validar_columna(valor: str):
    if not valor or not str(valor).strip():
        return False, "COLUMNA es requerida."
    try:
        numero = int(valor)
    except (ValueError, TypeError):
        return False, "COLUMNA debe ser un número entero."
    if not (1 <= numero <= 15):
        return False, "COLUMNA debe estar entre 1 y 15."
    return True, None


def validar_ip(valor: str):
    """
    Formato fijo de planta: 10.160.N.M
        - 1er bloque: fijo en 10
        - 2do bloque: fijo en 160
        - 3er bloque (N): entre 1 y 110
        - 4to bloque (M): libre, 0 a 255
    Ejemplo válido: 10.160.45.200
    """
    if not valor or not valor.strip():
        return False, "IP es requerida."
    patron = r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$"
    match = re.match(patron, valor.strip())
    if not match:
        return False, "IP debe tener formato IPv4 (ej: 10.160.45.200)."
    bloques = [int(g) for g in match.groups()]
    for b in bloques:
        if not (0 <= b <= 255):
            return False, "Cada bloque de la IP debe estar entre 0 y 255."
    if bloques[0] != 10 or bloques[1] != 160:
        return False, "La IP debe comenzar con 10.160 (ej: 10.160.45.200)."
    if not (1 <= bloques[2] <= 110):
        return False, "El tercer bloque de la IP debe estar entre 1 y 110."
    return True, None


def _validar_alfanumerico_17(valor: str, nombre_campo: str):
    if not valor or not valor.strip():
        return False, f"{nombre_campo} es requerido."
    valor = valor.strip()
    if len(valor) != 17:
        return False, f"{nombre_campo} debe tener exactamente 17 caracteres (tiene {len(valor)})."
    if not valor.isalnum():
        return False, f"{nombre_campo} debe ser alfanumérico (solo letras y números)."
    return True, None


def validar_sn_digital(valor: str):
    ok, error = _validar_alfanumerico_17(valor, "SN DIGITAL")
    if not ok:
        return ok, error
    septimo = valor.strip()[6].upper()
    if septimo != "U":
        return False, "El 7° carácter de SN DIGITAL debe ser la letra 'U'."
    return True, None


def validar_sn_fisica(valor: str):
    ok, error = _validar_alfanumerico_17(valor, "SN FÍSICA")
    if not ok:
        return ok, error
    septimo = valor.strip()[6].upper()
    if septimo not in ("B", "C", "D"):
        return False, "El 7° carácter de SN FÍSICA debe ser 'B', 'C' o 'D'."
    return True, None


def validar_mac(valor: str):
    if not valor or not valor.strip():
        return False, "MAC es requerida."
    patron = r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
    if not re.match(patron, valor.strip()):
        return False, "MAC debe tener formato XX:XX:XX:XX:XX:XX (hexadecimal)."
    return True, None


def validar_modelo(valor: str, sn_fisica: str):
    """
    MODELO ahora es un selector fijo con 3 opciones: 338T, 358T, 395T.
    Debe coincidir EXACTAMENTE con el valor esperado según el 7mo carácter
    de SN_FISICA (B->338T, C->358T, D->395T).
    """
    if not valor or not valor.strip():
        return False, "MODELO es requerido."
    if valor.strip() not in MODELO_POR_CARACTER.values():
        return False, "MODELO debe ser uno de: 338T, 358T, 395T."
    if not sn_fisica or len(sn_fisica.strip()) < 7:
        # No podemos cruzar la validación si SN_FISICA todavía no es válida;
        # ese error ya se reporta por separado al validar SN_FISICA.
        return True, None
    septimo = sn_fisica.strip()[6].upper()
    texto_esperado = MODELO_POR_CARACTER.get(septimo)
    if texto_esperado and valor.strip() != texto_esperado:
        return False, f"MODELO debe ser '{texto_esperado}' (según el 7° carácter de SN FÍSICA)."
    return True, None


def validar_psu_sn(valor: str):
    ok, error = _validar_alfanumerico_17(valor, "PSU SN")
    if not ok:
        return ok, error
    septimo = valor.strip()[6]
    if septimo not in ("0", "1"):
        return False, "El 7° carácter de PSU SN debe ser '0' o '1'."
    return True, None


def validar_chain(valor: str, nombre_campo: str):
    ok, error = _validar_alfanumerico_17(valor, nombre_campo)
    if not ok:
        return ok, error
    septimo = valor.strip()[6].upper()
    if septimo not in ("J", "1"):
        return False, f"El 7° carácter de {nombre_campo} debe ser 'J' o '1'."
    return True, None


def validar_contenedor(valor: str, plataforma: str):
    if not valor or not str(valor).strip():
        return False, "CONTENEDOR es requerido."
    if plataforma not in RANGOS_CONTENEDOR:
        return False, "Debe seleccionar una PLATAFORMA válida antes de elegir el CONTENEDOR."
    try:
        numero = int(valor)
    except (ValueError, TypeError):
        return False, "CONTENEDOR debe ser un número entero."
    minimo, maximo = RANGOS_CONTENEDOR[plataforma]
    if not (minimo <= numero <= maximo):
        return False, f"Para {plataforma}, CONTENEDOR debe estar entre {minimo} y {maximo}."
    return True, None


def validar_fila(valor: str, rack: str):
    if not valor or not str(valor).strip():
        return False, "FILA es requerida."
    try:
        numero = int(valor)
    except (ValueError, TypeError):
        return False, "FILA debe ser un número entero."

    if rack == "A":
        if not (1 <= numero <= 7):
            return False, "Para el Rack A, FILA debe estar entre 1 y 7."
    elif rack == "B":
        if not (8 <= numero <= 15):
            return False, "Para el Rack B, FILA debe estar entre 8 y 15."
    else:
        if not (1 <= numero <= 15):
            return False, "FILA debe estar entre 1 y 15."

    return True, None


# Mapa de validadores simples (los que no dependen de otros campos)
VALIDADORES_SIMPLES = {
    "IP": validar_ip,
    "SN_DIGITAL": validar_sn_digital,
    "SN_FISICA": validar_sn_fisica,
    "MAC": validar_mac,
    "PSU_SN": validar_psu_sn,
    "CHAIN_0": lambda v: validar_chain(v, "CHAIN 0"),
    "CHAIN_1": lambda v: validar_chain(v, "CHAIN 1"),
    "CHAIN_2": lambda v: validar_chain(v, "CHAIN 2"),
}
