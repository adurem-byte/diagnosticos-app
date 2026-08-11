/**
 * api.js
 * Capa centralizada de comunicación con el backend FastAPI.
 * Ningún otro archivo JS debe usar fetch() directamente: todos pasan por acá.
 */

const API = (() => {
  const BASE = ""; // mismo origen (FastAPI sirve también el frontend)

  async function _request(path, options = {}) {
    const respuesta = await fetch(BASE + path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });

    let cuerpo = null;
    try {
      cuerpo = await respuesta.json();
    } catch (_) {
      // sin cuerpo JSON (poco común en esta API)
    }

    if (!respuesta.ok) {
      const error = new Error("Error de API");
      error.status = respuesta.status;
      error.detail = cuerpo ? cuerpo.detail : null;
      throw error;
    }
    return cuerpo;
  }

  return {
    obtenerCatalogos() {
      return _request("/api/catalogos");
    },

    obtenerContenedores(plataforma) {
      return _request(`/api/contenedores/${encodeURIComponent(plataforma)}`);
    },

    obtenerReglas(diagnostico) {
      return _request(`/api/reglas/${encodeURIComponent(diagnostico)}`);
    },

    crearDiagnostico(datos) {
      return _request("/api/diagnosticos", {
        method: "POST",
        body: JSON.stringify(datos),
      });
    },

    listarDiagnosticos(soloPendientes = false) {
      const query = soloPendientes ? "?solo_pendientes=true" : "";
      return _request(`/api/diagnosticos${query}`);
    },

    resumenPendientes() {
      return _request("/api/pendientes/resumen");
    },

    adminLogin(usuario, password) {
      return _request("/api/admin/login", {
        method: "POST",
        body: JSON.stringify({ usuario, password }),
      });
    },

    adminLogout(token) {
      return _request("/api/admin/logout", {
        method: "POST",
        body: JSON.stringify({ token }),
      });
    },

    adminVerificar(token) {
      return _request("/api/admin/verificar", {
        method: "POST",
        body: JSON.stringify({ token }),
      });
    },

    adminAprobar(token, diagnosticoId) {
      return _request("/api/admin/aprobar", {
        method: "POST",
        body: JSON.stringify({ token, diagnostico_id: diagnosticoId }),
      });
    },

    adminEditar(token, diagnosticoId, datos) {
      return _request("/api/admin/editar", {
        method: "POST",
        body: JSON.stringify({ token, diagnostico_id: diagnosticoId, datos }),
      });
    },

    guardarDiagnosticadores(token, nombres) {
      return _request("/api/admin/diagnosticadores", {
        method: "POST",
        body: JSON.stringify({ token, nombres }),
      });
    },

    adminAnular(token, diagnosticoId, motivo) {
      return _request("/api/admin/anular", {
        method: "POST",
        body: JSON.stringify({ token, diagnostico_id: diagnosticoId, motivo }),
      });
    },
  };
})();
