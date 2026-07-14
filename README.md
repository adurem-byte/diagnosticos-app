# Diagnósticos de Máquinas

Sistema de diagnóstico para máquinas en plataformas de almacenamiento, con integración directa a Google Sheets.

**Demo en vivo:** [Próximamente en Replit]

## Características

- 📋 **Formulario dinámico** con validaciones según tipo de diagnóstico
- 🔧 **Ubicación:** Plataforma → Contenedor → Rack → Fila → Columna
- 🏷️ **Identificadores:** SN Digital, SN Física, MAC, Serial PSU
- ✅ **Panel de administrador** para aprobar/anular diagnósticos
- 🌓 **Tema claro/oscuro** automático
- ☁️ **Sincronización en tiempo real** con Google Sheets
- 🔐 **Autenticación** basada en token

## Stack

| Capa | Tecnología |
|------|-----------|
| **Backend** | FastAPI (Python) |
| **Frontend** | HTML5, CSS3, JavaScript vainilla |
| **Database** | Google Sheets (vía gspread API) |
| **Auth** | Bcrypt + Token-based sessions |
| **Hosting** | Replit (gratis) |

## Setup Local

### Requisitos
- Python 3.8+
- Google Cloud Service Account (JSON)

### Instalación

```bash
# 1. Clonar repo
git clone https://github.com/adurem/diagnosticos-app.git
cd diagnosticos-app

# 2. Crear virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env:
#   - SPREADSHEET_ID: ID de la planilla Google Sheets
#   - GOOGLE_CREDENTIALS_PATH: ruta a service_account.json
#   - SECRET_KEY: genera algo aleatorio

# 5. Correr backend
cd backend
uvicorn main:app --reload

# Frontend disponible en http://localhost:8000
```

## Variables de Entorno

Ver `.env.example` para template completo.

- `SPREADSHEET_ID` — ID de planilla Google Sheets (obligatorio)
- `GOOGLE_CREDENTIALS_PATH` — Ruta a service_account.json (local) o `GOOGLE_CREDENTIALS_B64` (Replit)
- `SECRET_KEY` — Clave secreta para tokens
- `APP_PORT` — Puerto (default: 8000)

## Google Sheets

### Setup Inicial

1. Google Cloud Console → crear proyecto
2. Habilitar Google Sheets API
3. IAM & Admin → Service Accounts → crear cuenta
4. Crear JSON key → descargar como `service_account.json`
5. Compartir planilla Google Sheets con el email de la service account

### Estructura de Sheets

Planilla requiere 3 pestañas:
- **Diagnosticos** — datos de diagnósticos (ID, FECHA_HORA, PLATAFORMA, CONTENEDOR, RACK, FILA, COLUMNA, etc)
- **Administradores** — usuarios admin con hashes bcrypt de contraseñas
- **Historial_Reparaciones** — historial de cambios por SN física

## API Endpoints

### Públicos
- `GET /` — Frontend
- `POST /api/catalogos` — Lista de catálogos (plataformas, racks, etc)
- `POST /api/pendientes/resumen` — Resumen de diagnósticos pendientes
- `POST /api/pendientes` — Listar diagnósticos sin aprobar

### Admin
- `POST /api/admin/login` — Iniciar sesión
- `POST /api/admin/logout` — Cerrar sesión
- `POST /api/admin/aprobar/<id>` — Aprobar diagnóstico
- `POST /api/admin/anular/<id>` — Anular diagnóstico

### Formulario
- `POST /api/obtener-reglas/<diagnostico>` — Reglas de campos para diagnóstico
- `POST /api/guardar-diagnostico` — Guardar nuevo diagnóstico

## Desarrollo

Ver `CONTRIBUTING.md` para instrucciones de contribución.

```bash
# Tests (próximamente)
pytest backend/

# Linting
black backend/
```

## Seguridad

⚠️ **IMPORTANTE:** Nunca commitees:
- `.env` — contiene SPREADSHEET_ID y SECRET_KEY
- `credentials/service_account.json` — credencial privada de Google Cloud

Ver `SECURITY.md` para más detalles.

## Troubleshooting

### "Error al conectar a Google Sheets"
- Verificar que `service_account.json` existe en `credentials/`
- Verificar permisos: la planilla debe estar compartida con el email de la service account
- En Replit: asegurar que `GOOGLE_CREDENTIALS_B64` está configurado en secrets

### "Validación falla aunque los datos parecen correctos"
- Ver `backend/validators.py` para reglas de validación
- Ver `backend/diagnostics_rules.py` para reglas por diagnóstico

### "Admin login no funciona"
- Verificar que la pestaña "Administradores" existe en la planilla
- Formato: usuario | contraseña_hash_bcrypt | nombre_completo

## Licencia

Privado (ver propietario)

## Contacto

adurem@proton.me
