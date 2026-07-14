/**
 * admin.js
 * Login de administrador y control de qué opciones del menú lateral
 * se muestran según haya o no una sesión de admin activa.
 *
 * El token vive solo en memoria (STATE.adminToken, definido en app.js).
 * Si se recarga la página, hay que volver a iniciar sesión — esto es
 * intencional para una herramienta de planta de uso compartido.
 */

function actualizarMenuAdmin() {
  const labelAdmin = document.getElementById("menu-admin-label");
  const btnAprobaciones = document.getElementById("menu-aprobaciones");
  const btnLogout = document.getElementById("menu-logout");
  const btnAdmin = document.getElementById("menu-admin");

  if (STATE.adminToken) {
    labelAdmin.textContent = "Admin: " + STATE.adminNombre;
    btnAdmin.classList.add("is-hidden");
    btnAprobaciones.classList.remove("is-hidden");
    btnLogout.classList.remove("is-hidden");
  } else {
    labelAdmin.textContent = "Acceso administrador";
    btnAdmin.classList.remove("is-hidden");
    btnAprobaciones.classList.add("is-hidden");
    btnLogout.classList.add("is-hidden");
  }
}

document.getElementById("menu-admin").addEventListener("click", function () {
  document.getElementById("login-usuario").value = "";
  document.getElementById("login-password").value = "";
  document.getElementById("login-error").style.display = "none";
  abrirModal("modal-login");
  cerrarSidebar();
  setTimeout(function () { document.getElementById("login-usuario").focus(); }, 150);
});

async function intentarLogin() {
  const usuario = document.getElementById("login-usuario").value.trim();
  const password = document.getElementById("login-password").value;
  const elError = document.getElementById("login-error");

  if (!usuario || !password) {
    elError.textContent = "Completá usuario y contraseña.";
    elError.style.display = "block";
    return;
  }

  const boton = document.getElementById("btn-login-submit");
  const textoOriginal = boton.textContent;
  boton.disabled = true;
  boton.textContent = "Ingresando…";

  try {
    const respuesta = await API.adminLogin(usuario, password);
    STATE.adminToken = respuesta.token;
    STATE.adminNombre = respuesta.nombre;
    actualizarMenuAdmin();
    cerrarModal("modal-login");
    mostrarToast("Sesión iniciada como " + respuesta.nombre + ".");
    if (!document.getElementById("view-registro").classList.contains("is-hidden")) {
      cargarRegistro();
    }
  } catch (err) {
    elError.textContent = "Usuario o contraseña incorrectos.";
    elError.style.display = "block";
  } finally {
    boton.disabled = false;
    boton.textContent = textoOriginal;
  }
}

document.getElementById("btn-login-submit").addEventListener("click", intentarLogin);
document.getElementById("login-password").addEventListener("keydown", function (e) {
  if (e.key === "Enter") intentarLogin();
});

document.getElementById("menu-aprobaciones").addEventListener("click", function () {
  mostrarVista("registro");
  document.getElementById("registro-filtro-estado").value = "pendientes";
  cargarRegistro();
  cerrarSidebar();
});

document.getElementById("menu-logout").addEventListener("click", async function () {
  try {
    if (STATE.adminToken) await API.adminLogout(STATE.adminToken);
  } catch (err) {
    // si falla el logout en backend, igual limpiamos el estado local
  }
  STATE.adminToken = null;
  STATE.adminNombre = null;
  actualizarMenuAdmin();
  cerrarSidebar();
  mostrarToast("Sesión de administrador cerrada.");
  if (!document.getElementById("view-registro").classList.contains("is-hidden")) {
    cargarRegistro();
  }
});

// Estado inicial del menú (sin sesión)
actualizarMenuAdmin();
