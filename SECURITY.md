# Security Guidelines

## Credenciales y Secretos

**NUNCA commitees estos archivos:**
- `.env` — Contiene `SPREADSHEET_ID`, `SECRET_KEY`
- `credentials/service_account.json` — Credencial privada de Google Cloud

Ambos están en `.gitignore` y están protegidos.

## En Production (Replit)

Las credenciales se configuran de forma segura en el dashboard de Replit:
1. Variables de entorno (`SPREADSHEET_ID`, `SECRET_KEY`)
2. `GOOGLE_CREDENTIALS_B64` — JSON de service account encodificado en base64 (sin subir archivos)

Replit protege estos valores y nunca los expone en logs públicos.

## Rotación de Credenciales

Google Cloud Service Account key debe rotarse regularmente:
1. Google Cloud Console → IAM & Admin → Service Accounts
2. Eliminar key antigua, generar nueva
3. Actualizar en `.env` (local) y Replit dashboard (production)

## Reportar Vulnerabilidades

Si encuentras una vulnerabilidad de seguridad, por favor contacta de forma privada en lugar de publicarla en issues.
