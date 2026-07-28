/**
 * app.js
 * Lógica principal de la interfaz: formulario dinámico, validaciones de
 * formato (réplica en cliente de backend/validators.py), sidebar, modo
 * oscuro, banner de pendientes y vista de "Registro de diagnósticos".
 *
 * IMPORTANTE: estas validaciones son solo para dar feedback inmediato al
 * usuario. El backend (backend/validators.py + backend/main.py) vuelve a
 * validar todo antes de guardar — nunca confiamos solo en esto.
 */

// ---------------------------------------------------------------------------
// Estado global simple de la app en memoria. adminToken/adminNombre se
// restauran desde localStorage al cargar la página (ver restaurarSesion()
// en admin.js) para que la sesión de admin sobreviva a un refresh.
// ---------------------------------------------------------------------------
const STATE = {
  catalogos: null,
  reglasPorDiagnostico: {},
  reglasActuales: null,
  adminToken: null,
  adminNombre: null,
};

// ---------------------------------------------------------------------------
// Utilidades de UI: toasts, modales
// ---------------------------------------------------------------------------
function mostrarToast(mensaje, tipo) {
  tipo = tipo || "ok";
  const contenedor = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = "toast" + (tipo === "error" ? " toast-error" : "");
  toast.textContent = mensaje;
  contenedor.appendChild(toast);
  setTimeout(function () { toast.remove(); }, 4200);
}

function abrirModal(id) {
  document.getElementById(id).classList.add("is-open");
}
function cerrarModal(id) {
  document.getElementById(id).classList.remove("is-open");
}
document.querySelectorAll("[data-close-modal]").forEach(function (btn) {
  btn.addEventListener("click", function () { cerrarModal(btn.dataset.closeModal); });
});
document.querySelectorAll(".modal-overlay").forEach(function (overlay) {
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) overlay.classList.remove("is-open");
  });
});

// ---------------------------------------------------------------------------
// Validadores de formato (réplica de backend/validators.py)
// ---------------------------------------------------------------------------
const RANGOS_CONTENEDOR = {
  "PLATAFORMA 1": [1, 12],
  "PLATAFORMA 2": [13, 30],
  "PLATAFORMA 3": [31, 54],
  "PLATAFORMA 4": [55, 78],
  "PLATAFORMA 5": [79, 94],
  "PLATAFORMA 6": [95, 110],
};

const MODELO_POR_CARACTER = { B: "338T", C: "358T", D: "395T" };

function validarColumna(valor) {
  if (!valor || !String(valor).trim()) return { ok: false, error: "COLUMNA es requerida." };
  const numero = parseInt(valor, 10);
  if (Number.isNaN(numero) || String(numero) !== String(valor).trim()) {
    return { ok: false, error: "COLUMNA debe ser un número entero." };
  }
  if (numero < 1 || numero > 15) return { ok: false, error: "COLUMNA debe estar entre 1 y 15." };
  return { ok: true };
}

function validarFila(valor, rack) {
  if (!valor || !String(valor).trim()) return { ok: false, error: "FILA es requerida." };
  const numero = parseInt(valor, 10);
  if (Number.isNaN(numero) || String(numero) !== String(valor).trim()) {
    return { ok: false, error: "FILA debe ser un número entero." };
  }
  if (rack === "A") {
    if (numero < 1 || numero > 7) return { ok: false, error: "Para el Rack A, FILA debe estar entre 1 y 7." };
  } else if (rack === "B") {
    if (numero < 8 || numero > 15) return { ok: false, error: "Para el Rack B, FILA debe estar entre 8 y 15." };
  } else {
    if (numero < 1 || numero > 15) return { ok: false, error: "FILA debe estar entre 1 y 15." };
  }
  return { ok: true };
}

function validarIp(valor) {
  if (!valor || !valor.trim()) return { ok: false, error: "IP es requerida." };
  const match = valor.trim().match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (!match) return { ok: false, error: "IP debe tener formato IPv4 (ej: 10.160.45.200)." };
  const bloques = match.slice(1, 5).map(Number);
  for (let i = 0; i < bloques.length; i++) {
    if (bloques[i] < 0 || bloques[i] > 255) return { ok: false, error: "Cada bloque de la IP debe estar entre 0 y 255." };
  }
  if (bloques[0] !== 10 || bloques[1] !== 160) {
    return { ok: false, error: "La IP debe comenzar con 10.160 (ej: 10.160.45.200)." };
  }
  if (bloques[2] < 1 || bloques[2] > 110) return { ok: false, error: "El tercer bloque de la IP debe estar entre 1 y 110." };
  return { ok: true };
}

function _validarAlfanumerico17(valor, nombreCampo) {
  if (!valor || !valor.trim()) return { ok: false, error: nombreCampo + " es requerido." };
  const v = valor.trim();
  if (v.length !== 17) return { ok: false, error: nombreCampo + " debe tener exactamente 17 caracteres (tiene " + v.length + ")." };
  if (!/^[a-zA-Z0-9]+$/.test(v)) return { ok: false, error: nombreCampo + " debe ser alfanumérico (solo letras y números)." };
  return { ok: true };
}

function validarSnDigital(valor) {
  const base = _validarAlfanumerico17(valor, "SN DIGITAL");
  if (!base.ok) return base;
  const septimo = valor.trim()[6].toUpperCase();
  if (septimo !== "U") return { ok: false, error: "El 7° carácter de SN DIGITAL debe ser la letra 'U'." };
  return { ok: true };
}

function validarSnFisica(valor) {
  const base = _validarAlfanumerico17(valor, "SN FÍSICA");
  if (!base.ok) return base;
  const septimo = valor.trim()[6].toUpperCase();
  if (["B", "C", "D"].indexOf(septimo) === -1) return { ok: false, error: "El 7° carácter de SN FÍSICA debe ser 'B', 'C' o 'D'." };
  return { ok: true };
}

function validarMac(valor) {
  if (!valor || !valor.trim()) return { ok: false, error: "MAC es requerida." };
  if (!/^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/.test(valor.trim())) {
    return { ok: false, error: "MAC debe tener formato XX:XX:XX:XX:XX:XX (hexadecimal)." };
  }
  return { ok: true };
}

function validarModelo(valor, snFisica) {
  if (!valor || !valor.trim()) return { ok: false, error: "MODELO es requerido." };
  if (Object.values(MODELO_POR_CARACTER).indexOf(valor.trim()) === -1) {
    return { ok: false, error: "MODELO debe ser uno de: 338T, 358T, 395T." };
  }
  if (!snFisica || snFisica.trim().length < 7) return { ok: true };
  const septimo = snFisica.trim()[6].toUpperCase();
  const esperado = MODELO_POR_CARACTER[septimo];
  if (esperado && valor.trim() !== esperado) {
    return { ok: false, error: "MODELO debe ser '" + esperado + "' (según el 7° carácter de SN FÍSICA)." };
  }
  return { ok: true };
}

function validarPsuSn(valor) {
  const base = _validarAlfanumerico17(valor, "PSU SN");
  if (!base.ok) return base;
  const septimo = valor.trim()[6];
  if (["0", "1"].indexOf(septimo) === -1) return { ok: false, error: "El 7° carácter de PSU SN debe ser '0' o '1'." };
  return { ok: true };
}

function validarChain(valor, nombreCampo) {
  const base = _validarAlfanumerico17(valor, nombreCampo);
  if (!base.ok) return base;
  const septimo = valor.trim()[6].toUpperCase();
  if (["J", "1"].indexOf(septimo) === -1) return { ok: false, error: "El 7° carácter de " + nombreCampo + " debe ser 'J' o '1'." };
  return { ok: true };
}

function validarContenedor(valor, plataforma) {
  if (!valor || !String(valor).trim()) return { ok: false, error: "CONTENEDOR es requerido." };
  const rango = RANGOS_CONTENEDOR[plataforma];
  if (!rango) return { ok: false, error: "Debe seleccionar una PLATAFORMA válida antes de elegir el CONTENEDOR." };
  const numero = parseInt(valor, 10);
  if (Number.isNaN(numero)) return { ok: false, error: "CONTENEDOR debe ser un número entero." };
  if (numero < rango[0] || numero > rango[1]) {
    return { ok: false, error: "Para " + plataforma + ", CONTENEDOR debe estar entre " + rango[0] + " y " + rango[1] + "." };
  }
  return { ok: true };
}

const VALIDADORES_SIMPLES = {
  COLUMNA: validarColumna,
  IP: validarIp,
  SN_DIGITAL: validarSnDigital,
  SN_FISICA: validarSnFisica,
  MAC: validarMac,
  PSU_SN: validarPsuSn,
  CHAIN_0: function (v) { return validarChain(v, "CHAIN 0"); },
  CHAIN_1: function (v) { return validarChain(v, "CHAIN 1"); },
  CHAIN_2: function (v) { return validarChain(v, "CHAIN 2"); },
};

// ---------------------------------------------------------------------------
// Mapeo de campos del modelo de datos -> elementos del DOM
// ---------------------------------------------------------------------------
const CAMPOS = [
  "PLATAFORMA", "CONTENEDOR", "RACK", "FILA", "COLUMNA", "DIAGNOSTICO",
  "IP", "SN_DIGITAL", "SN_FISICA", "MAC", "MODELO", "TIPO_PIEZA",
  "PSU_SN", "CHAIN_0", "CHAIN_1", "CHAIN_2", "FUGA", "ESTADO",
  "SUPERVISOR", "OBSERVACION",
];

function idInputDe(campo) {
  return "f-" + campo.toLowerCase().replace(/_/g, "-");
}
function elementoDe(campo) {
  return document.getElementById(idInputDe(campo));
}
function wrapperDe(campo) {
  return document.querySelector('[data-field="' + campo + '"]');
}
function valorDe(campo) {
  const el = elementoDe(campo);
  return el ? el.value : "";
}

// ---------------------------------------------------------------------------
// Carga inicial de catálogos y armado de selects
// ---------------------------------------------------------------------------
function llenarSelect(elemento, opciones, placeholder) {
  elemento.innerHTML = "";
  if (placeholder) {
    const op = document.createElement("option");
    op.value = "";
    op.textContent = placeholder;
    elemento.appendChild(op);
  }
  opciones.forEach(function (valor) {
    const op = document.createElement("option");
    op.value = valor;
    op.textContent = valor;
    elemento.appendChild(op);
  });
}

async function inicializarCatalogos() {
  const catalogos = await API.obtenerCatalogos();
  STATE.catalogos = catalogos;

  llenarSelect(elementoDe("PLATAFORMA"), catalogos.plataformas, "Seleccionar…");
  llenarSelect(elementoDe("RACK"), catalogos.racks, "Seleccionar…");
  llenarSelect(elementoDe("DIAGNOSTICO"), catalogos.diagnosticos, "Seleccionar diagnóstico…");
  llenarSelect(elementoDe("MODELO"), catalogos.modelo_opciones, "Seleccionar…");
  llenarSelect(elementoDe("TIPO_PIEZA"), catalogos.tipos_pieza, "Seleccionar…");
  llenarSelect(elementoDe("FUGA"), catalogos.fuga_opciones, "Seleccionar…");
  llenarSelect(elementoDe("ESTADO"), catalogos.estado_opciones, "Seleccionar…");
  llenarSelect(elementoDe("SUPERVISOR"), catalogos.supervisores, "Seleccionar…");

  llenarSelect(document.getElementById("registro-filtro-diagnostico"), catalogos.diagnosticos, "Todas las fallas");
  llenarSelect(document.getElementById("registro-filtro-plataforma"), catalogos.plataformas, "Todas las plataformas");
  llenarSelect(document.getElementById("registro-filtro-supervisor"), catalogos.supervisores, "Todos los diagnosticadores");
}

elementoDe("PLATAFORMA").addEventListener("change", async function (e) {
  const plataforma = e.target.value;
  const selectContenedor = elementoDe("CONTENEDOR");
  if (!plataforma) {
    selectContenedor.innerHTML = '<option value="">Elegí una plataforma primero</option>';
    selectContenedor.disabled = true;
    return;
  }
  try {
    const respuesta = await API.obtenerContenedores(plataforma);
    llenarSelect(selectContenedor, respuesta.contenedores, "Seleccionar…");
    selectContenedor.disabled = false;
  } catch (err) {
    mostrarToast("No se pudieron cargar los contenedores.", "error");
  }
});

elementoDe("RACK").addEventListener("change", function (e) {
  const rack = e.target.value;
  const inputFila = elementoDe("FILA");
  if (!inputFila) return;
  if (rack === "A") {
    inputFila.min = "1";
    inputFila.max = "7";
    inputFila.placeholder = "1 a 7";
  } else if (rack === "B") {
    inputFila.min = "8";
    inputFila.max = "15";
    inputFila.placeholder = "8 a 15";
  } else {
    inputFila.min = "1";
    inputFila.max = "15";
    inputFila.placeholder = "1 a 15";
  }
  if (inputFila.value) validarCampoIndividual("FILA");
});

elementoDe("FILA").addEventListener("input", function (e) {
  const rack = valorDe("RACK");
  let val = parseInt(e.target.value, 10);
  if (isNaN(val)) return;

  if (rack === "A" && val > 7) {
    e.target.value = 7;
    validarCampoIndividual("FILA");
  } else if (rack === "B" && val > 15) {
    e.target.value = 15;
    validarCampoIndividual("FILA");
  } else if (!rack && val > 15) {
    e.target.value = 15;
    validarCampoIndividual("FILA");
  }
});

// ---------------------------------------------------------------------------
// Lógica dinámica de campos según el DIAGNÓSTICO elegido
// ---------------------------------------------------------------------------
async function obtenerReglas(diagnostico) {
  if (STATE.reglasPorDiagnostico[diagnostico]) {
    return STATE.reglasPorDiagnostico[diagnostico];
  }
  const respuesta = await API.obtenerReglas(diagnostico);
  STATE.reglasPorDiagnostico[diagnostico] = respuesta.reglas;
  return respuesta.reglas;
}

function aplicarReglasAlFormulario(reglas) {
  STATE.reglasActuales = reglas;

  CAMPOS.forEach(function (campo) {
    if (campo === "DIAGNOSTICO") return;
    const wrapper = wrapperDe(campo);
    if (!wrapper) return;
    const nivel = reglas[campo];
    const input = elementoDe(campo);

    wrapper.classList.remove("is-hidden", "field--required", "field--optional");
    if (input) input.required = false;

    if (nivel === "NO_NECESARIO") {
      wrapper.classList.add("is-hidden");
      if (input) { input.value = ""; input.classList.remove("is-invalid"); }
      wrapper.classList.remove("has-error");
    } else if (nivel === "OBLIGATORIO") {
      wrapper.classList.add("field--required");
      if (input) input.required = true;
    } else if (nivel === "OPCIONAL") {
      wrapper.classList.add("field--optional");
    }
  });
}

elementoDe("DIAGNOSTICO").addEventListener("change", async function (e) {
  const diagnostico = e.target.value;
  if (!diagnostico) return;
  try {
    const reglas = await obtenerReglas(diagnostico);
    aplicarReglasAlFormulario(reglas);
  } catch (err) {
    mostrarToast("No se pudieron cargar las reglas del diagnóstico.", "error");
  }
});

// ---------------------------------------------------------------------------
// Validación de un campo individual (feedback visual inmediato al salir del campo)
// ---------------------------------------------------------------------------
function marcarError(campo, mensaje) {
  const wrapper = wrapperDe(campo);
  const input = elementoDe(campo);
  if (!wrapper || !input) return;
  wrapper.classList.add("has-error");
  input.classList.add("is-invalid");
  const spanError = wrapper.querySelector(".field__error");
  if (spanError) spanError.textContent = mensaje;
}

function limpiarError(campo) {
  const wrapper = wrapperDe(campo);
  const input = elementoDe(campo);
  if (!wrapper || !input) return;
  wrapper.classList.remove("has-error");
  input.classList.remove("is-invalid");
}

function validarCampoIndividual(campo) {
  const nivel = STATE.reglasActuales ? STATE.reglasActuales[campo] : null;
  if (nivel === "NO_NECESARIO") return true;

  const valor = valorDe(campo).trim();

  if (!valor) {
    if (nivel === "OBLIGATORIO") {
      marcarError(campo, "Este campo es obligatorio.");
      return false;
    }
    limpiarError(campo);
    return true;
  }

  let resultado = { ok: true };
  if (campo === "CONTENEDOR") {
    resultado = validarContenedor(valor, valorDe("PLATAFORMA"));
  } else if (campo === "FILA") {
    resultado = validarFila(valor, valorDe("RACK"));
  } else if (campo === "MODELO") {
    resultado = validarModelo(valor, valorDe("SN_FISICA"));
  } else if (VALIDADORES_SIMPLES[campo]) {
    resultado = VALIDADORES_SIMPLES[campo](valor);
  }

  if (!resultado.ok) {
    marcarError(campo, resultado.error);
    return false;
  }
  limpiarError(campo);
  return true;
}

Object.keys(VALIDADORES_SIMPLES).concat(["CONTENEDOR", "FILA", "MODELO"]).forEach(function (campo) {
  const input = elementoDe(campo);
  if (input) {
    input.addEventListener("blur", function () { validarCampoIndividual(campo); });
    input.addEventListener("change", function () { validarCampoIndividual(campo); });
    input.addEventListener("input", function () {
      if (wrapperDe(campo).classList.contains("has-error")) validarCampoIndividual(campo);
    });
  }
});
elementoDe("SN_FISICA").addEventListener("input", function () {
  const snFisica = valorDe("SN_FISICA").trim();
  if (snFisica.length >= 7) {
    const septimo = snFisica[6].toUpperCase();
    const esperado = MODELO_POR_CARACTER[septimo];
    if (esperado) {
      elementoDe("MODELO").value = esperado;
      limpiarError("MODELO");
    }
  }
  if (valorDe("MODELO").trim()) validarCampoIndividual("MODELO");
});

// ---------------------------------------------------------------------------
// Validación completa + envío del formulario
// ---------------------------------------------------------------------------
function recolectarDatosFormulario() {
  const datos = {};
  CAMPOS.forEach(function (campo) { datos[campo] = valorDe(campo); });
  return datos;
}

function validarFormularioCompleto() {
  if (!STATE.reglasActuales) {
    return ["Seleccioná un DIAGNÓSTICO antes de continuar."];
  }
  const errores = [];
  CAMPOS.forEach(function (campo) {
    const nivel = STATE.reglasActuales[campo];
    if (nivel === "NO_NECESARIO") return;
    const valido = validarCampoIndividual(campo);
    if (!valido) {
      const wrapper = wrapperDe(campo);
      const mensaje = wrapper ? wrapper.querySelector(".field__error").textContent : (campo + " inválido.");
      errores.push(mensaje);
    }
  });

  const campos_sn = ["SN_DIGITAL", "SN_FISICA", "PSU_SN", "CHAIN_0", "CHAIN_1", "CHAIN_2"];
  const sns_ingresados = [];
  campos_sn.forEach(function(c_sn) {
    const val_sn = valorDe(c_sn).trim().toUpperCase();
    if (val_sn) sns_ingresados.push(val_sn);
  });
  const uniques = new Set(sns_ingresados);
  if (uniques.size !== sns_ingresados.length) {
    errores.push("No se permiten números de serie (SN) duplicados en un mismo diagnóstico.");
  }

  return errores;
}

document.getElementById("btn-confirmar-diagnostico").addEventListener("click", async function () {
  const errores = validarFormularioCompleto();
  if (errores.length > 0) {
    const lista = document.getElementById("lista-errores");
    lista.innerHTML = "";
    errores.forEach(function (msg) {
      const li = document.createElement("li");
      li.textContent = msg;
      lista.appendChild(li);
    });
    abrirModal("modal-errores");
    return;
  }

  const boton = document.getElementById("btn-confirmar-diagnostico");
  const textoOriginal = boton.innerHTML;
  boton.disabled = true;
  boton.innerHTML = '<span class="spinner"></span> Guardando…';

  try {
    const datos = recolectarDatosFormulario();
    const respuesta = await API.crearDiagnostico(datos);
    document.getElementById("modal-exito-id").textContent = respuesta.id;
    abrirModal("modal-exito");
    await actualizarBannerPendientes();
  } catch (err) {
    if (err.status === 422 && err.detail && err.detail.errores) {
      const lista = document.getElementById("lista-errores");
      lista.innerHTML = "";
      err.detail.errores.forEach(function (msg) {
        const li = document.createElement("li");
        li.textContent = msg;
        lista.appendChild(li);
      });
      abrirModal("modal-errores");
    } else {
      mostrarToast("Ocurrió un error al guardar el diagnóstico. Intentá nuevamente.", "error");
    }
  } finally {
    boton.disabled = false;
    boton.innerHTML = textoOriginal;
  }
});

document.getElementById("btn-exito-cerrar").addEventListener("click", function () {
  cerrarModal("modal-exito");
  document.getElementById("diagnostico-form").reset();
  CAMPOS.forEach(function (campo) {
    if (campo === "DIAGNOSTICO") return;
    const wrapper = wrapperDe(campo);
    if (wrapper) wrapper.classList.add("is-hidden");
  });
  elementoDe("CONTENEDOR").innerHTML = '<option value="">Elegí una plataforma primero</option>';
  elementoDe("CONTENEDOR").disabled = true;
  STATE.reglasActuales = null;
  window.scrollTo({ top: 0, behavior: "smooth" });
});

// ---------------------------------------------------------------------------
// Banner de pendientes (visible siempre, sin necesidad de admin)
// ---------------------------------------------------------------------------
async function actualizarBannerPendientes() {
  const banner = document.getElementById("status-banner");
  const texto = document.getElementById("status-banner-text");
  try {
    const resumen = await API.resumenPendientes();
    if (resumen.total_pendientes === 0) {
      banner.classList.add("is-empty");
      texto.innerHTML = "<strong>Sin traslados pendientes.</strong> Todas las solicitudes están aprobadas.";
      return;
    }
    banner.classList.remove("is-empty");
    const partes = Object.entries(resumen.por_supervisor)
      .map(function (par) { return "<strong>" + par[0] + "</strong>: " + par[1]; })
      .join(" · ");
    texto.innerHTML = "<strong>" + resumen.total_pendientes + " traslado(s) pendiente(s)</strong> de aprobación — " + partes;
  } catch (err) {
    texto.textContent = "No se pudo cargar el estado de traslados pendientes.";
  }
}

// ---------------------------------------------------------------------------
// Sidebar (menú hamburguesa)
// ---------------------------------------------------------------------------
const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebar-overlay");

function abrirSidebar() {
  sidebar.classList.add("is-open");
  sidebarOverlay.classList.add("is-open");
}
function cerrarSidebar() {
  sidebar.classList.remove("is-open");
  sidebarOverlay.classList.remove("is-open");
}
document.getElementById("btn-open-sidebar").addEventListener("click", abrirSidebar);
document.getElementById("btn-close-sidebar").addEventListener("click", cerrarSidebar);
sidebarOverlay.addEventListener("click", cerrarSidebar);

document.getElementById("menu-nuevo-diagnostico").addEventListener("click", function () {
  mostrarVista("form");
  cerrarSidebar();
});
document.getElementById("menu-registro").addEventListener("click", function () {
  mostrarVista("registro");
  cargarRegistro();
  cerrarSidebar();
});

// ---------------------------------------------------------------------------
// Cambio de vista (Formulario <-> Registro)
// ---------------------------------------------------------------------------
function mostrarVista(nombre) {
  const viewForm = document.getElementById("view-form");
  const viewRegistro = document.getElementById("view-registro");
  const stickyBar = document.getElementById("sticky-bar-form");

  if (nombre === "form") {
    viewForm.classList.remove("is-hidden");
    viewRegistro.classList.add("is-hidden");
    stickyBar.style.display = "flex";
  } else {
    viewForm.classList.add("is-hidden");
    viewRegistro.classList.remove("is-hidden");
    stickyBar.style.display = "none";
  }
  window.scrollTo({ top: 0 });
}

// ---------------------------------------------------------------------------
// Vista: Registro de diagnósticos
// ---------------------------------------------------------------------------
function badgeEstado(fila) {
  if (String(fila.ANULADO).toUpperCase() === "SI") return '<span class="badge badge-void">Anulado</span>';
  if (String(fila.APROBADO).toUpperCase() === "SI") return '<span class="badge badge-approved">Aprobado</span>';
  return '<span class="badge badge-pending">Pendiente</span>';
}

function renderizarRegistro(filas) {
  const lista = document.getElementById("registro-lista");
  if (filas.length === 0) {
    lista.innerHTML =
      '<div class="empty-state">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="3" width="18" height="18" rx="2"/></svg>' +
      "<p>No hay diagnósticos para mostrar con este filtro.</p>" +
      "</div>";
    return;
  }

  lista.innerHTML = filas.map(function (fila) {
    const esAdmin = !!STATE.adminToken;
    const puedeAnular = esAdmin && String(fila.ANULADO).toUpperCase() !== "SI";
    const puedeAprobar = esAdmin && String(fila.APROBADO).toUpperCase() !== "SI" && String(fila.ANULADO).toUpperCase() !== "SI";
    const fechaPiezas = fila.FECHA_PIEZAS_CAMBIADAS || null;
    const fechaReparacion = fila.FECHA_REPARACION || null;
    const fechaGarantia = fila.FECHA_VENCIMIENTO_GARANTIA || null;
    const tieneAntecedentes = !!(fechaPiezas || fechaReparacion);

    return (
      '<div class="record-card" data-id="' + fila.ID + '">' +
      '<div class="record-card__top"><div>' +
      '<div class="record-card__id">' + fila.ID + "</div>" +
      '<div class="record-card__diag">' + fila.DIAGNOSTICO + "</div>" +
      "</div>" + badgeEstado(fila) + "</div>" +
      '<div class="record-card__meta">' +
      "<div>Ubicación: <b>" + (fila.PLATAFORMA || "—") + " / Cont. " + (fila.CONTENEDOR || "—") + " / Rack " + (fila.RACK || "—") + "</b></div>" +
      "<div>Fila/Col: <b>" + (fila.FILA || "—") + " / " + (fila.COLUMNA || "—") + "</b></div>" +
      "<div>SN Física: <b class=\"mono-input\" style=\"font-size:12px;\">" + (fila.SN_FISICA || "—") + "</b></div>" +
      "<div>MAC: <b class=\"mono-input\" style=\"font-size:12px;\">" + (fila.MAC || "—") + "</b></div>" +
      "<div>Diagnosticador: <b>" + (fila.SUPERVISOR || "—") + "</b></div>" +
      "<div>Fecha: <b>" + (fila.FECHA_HORA || "—") + "</b></div>" +
      "</div>" +
      (esAdmin
        ? ('<div class="repair-history ' + (tieneAntecedentes ? "repair-history--warning" : "repair-history--ok") + '">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          (tieneAntecedentes
            ? '<path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="10"/>'
            : '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>') +
          "</svg>" +
          '<div class="repair-history__lines">' +
          "<div>Últ. pieza cambiada: <b>" + (fechaPiezas || "Sin datos") + "</b></div>" +
          "<div>Últ. reparación: <b>" + (fechaReparacion || "Sin datos") + "</b></div>" +
          "<div>Vencimiento de garantía: <b>" + (fechaGarantia || "Sin datos") + "</b></div>" +
          "</div>" +
          "</div>")
        : "") +
      ((puedeAprobar || puedeAnular)
        ? '<div class="record-card__actions">' +
          (puedeAprobar ? '<button class="btn btn-success btn-sm" data-aprobar="' + fila.ID + '">Aprobar traslado</button>' : "") +
          (puedeAnular ? '<button class="btn btn-danger btn-sm" data-anular="' + fila.ID + '">Anular</button>' : "") +
          "</div>"
        : "") +
      "</div>"
    );
  }).join("");

  lista.querySelectorAll("[data-aprobar]").forEach(function (btn) {
    btn.addEventListener("click", function () { aprobarDesdeRegistro(btn.dataset.aprobar); });
  });
  lista.querySelectorAll("[data-anular]").forEach(function (btn) {
    btn.addEventListener("click", function () { abrirModalAnular(btn.dataset.anular); });
  });
}

async function cargarRegistro() {
  const lista = document.getElementById("registro-lista");
  lista.innerHTML = '<div class="skeleton-line" style="height:70px; border-radius:12px;"></div>';
  try {
    const filtro = document.getElementById("registro-filtro-estado").value;
    const respuesta = await API.listarDiagnosticos(false);
    let filtrados = respuesta.diagnosticos;
    if (filtro === "pendientes") {
      filtrados = filtrados.filter(function (f) { return String(f.APROBADO).toUpperCase() === "NO" && String(f.ANULADO).toUpperCase() !== "SI"; });
    } else if (filtro === "aprobados") {
      filtrados = filtrados.filter(function (f) { return String(f.APROBADO).toUpperCase() === "SI"; });
    } else if (filtro === "anulados") {
      filtrados = filtrados.filter(function (f) { return String(f.ANULADO).toUpperCase() === "SI"; });
    }

    const filtroDiagnostico = document.getElementById("registro-filtro-diagnostico").value;
    const filtroPlataforma = document.getElementById("registro-filtro-plataforma").value;
    const filtroSupervisor = document.getElementById("registro-filtro-supervisor").value;
    const busqueda = document.getElementById("registro-busqueda").value.trim().toUpperCase();

    if (filtroDiagnostico) {
      filtrados = filtrados.filter(function (f) { return f.DIAGNOSTICO === filtroDiagnostico; });
    }
    if (filtroPlataforma) {
      filtrados = filtrados.filter(function (f) { return f.PLATAFORMA === filtroPlataforma; });
    }
    if (filtroSupervisor) {
      filtrados = filtrados.filter(function (f) { return f.SUPERVISOR === filtroSupervisor; });
    }
    if (busqueda) {
      filtrados = filtrados.filter(function (f) {
        return (f.SN_FISICA || "").toUpperCase().includes(busqueda) ||
          (f.MAC || "").toUpperCase().includes(busqueda);
      });
    }

    filtrados = filtrados.slice().reverse();
    renderizarRegistro(filtrados);
  } catch (err) {
    document.getElementById("registro-lista").innerHTML = '<div class="empty-state"><p>No se pudo cargar el registro.</p></div>';
  }
}

document.getElementById("registro-filtro-estado").addEventListener("change", cargarRegistro);
document.getElementById("registro-filtro-diagnostico").addEventListener("change", cargarRegistro);
document.getElementById("registro-filtro-plataforma").addEventListener("change", cargarRegistro);
document.getElementById("registro-filtro-supervisor").addEventListener("change", cargarRegistro);
document.getElementById("registro-busqueda").addEventListener("input", cargarRegistro);
document.getElementById("btn-refrescar-registro").addEventListener("click", cargarRegistro);

async function aprobarDesdeRegistro(id) {
  if (!STATE.adminToken) return;
  try {
    await API.adminAprobar(STATE.adminToken, id);
    mostrarToast("Traslado " + id + " aprobado.");
    await cargarRegistro();
    await actualizarBannerPendientes();
  } catch (err) {
    mostrarToast("No se pudo aprobar el traslado.", "error");
  }
}

let _idAAnular = null;
function abrirModalAnular(id) {
  _idAAnular = id;
  document.getElementById("modal-anular-id").textContent = id;
  document.getElementById("anular-motivo").value = "";
  abrirModal("modal-anular");
}
document.getElementById("btn-anular-confirmar").addEventListener("click", async function () {
  if (!_idAAnular || !STATE.adminToken) return;
  const motivo = document.getElementById("anular-motivo").value.trim();
  try {
    await API.adminAnular(STATE.adminToken, _idAAnular, motivo);
    mostrarToast("Registro " + _idAAnular + " anulado.");
    cerrarModal("modal-anular");
    await cargarRegistro();
    await actualizarBannerPendientes();
  } catch (err) {
    mostrarToast("No se pudo anular el registro.", "error");
  }
});

// ---------------------------------------------------------------------------
// Modo oscuro
// ---------------------------------------------------------------------------
function aplicarTema(tema) {
  document.documentElement.setAttribute("data-theme", tema);
  document.getElementById("theme-toggle").setAttribute("aria-checked", tema === "dark");
}
document.getElementById("theme-toggle").addEventListener("click", function () {
  const actual = document.documentElement.getAttribute("data-theme");
  aplicarTema(actual === "dark" ? "light" : "dark");
});
if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
  aplicarTema("dark");
}

// ---------------------------------------------------------------------------
// Inicialización
// ---------------------------------------------------------------------------
(async function init() {
  mostrarVista("form"); // estado inicial explícito: formulario visible, registro oculto
  try {
    await inicializarCatalogos();
  } catch (err) {
    mostrarToast("No se pudieron cargar los catálogos. Revisá la conexión con el servidor.", "error");
  }
  actualizarBannerPendientes();
})();
