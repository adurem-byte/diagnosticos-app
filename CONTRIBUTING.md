# Contributing

## Setup Local

```bash
# Clonar repo
git clone https://github.com/adurem/diagnosticos-app.git
cd diagnosticos-app

# Python venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Dependencias
pip install -r requirements.txt

# Copiar .env template y configurar
cp .env.example .env
# Editar .env con credenciales reales (Google Sheets ID, service account JSON path)

# Correr backend
cd backend
uvicorn main:app --reload
# Frontend en http://localhost:8000
```

## Workflow de Cambios

1. Fork el repo (si no eres colaborador directo)
2. Crear branch: `git checkout -b feature/tu-feature`
3. Hacer cambios
4. Commit: `git commit -m "feat: descripción clara"`
5. Push: `git push origin feature/tu-feature`
6. Crear Pull Request

## Requisitos antes de mergear

- Tests deben pasar (si existen)
- Code review de al menos 1 colaborador
- Asegurar que `.env` y `credentials/` NO están en los commits

## Seguridad

- Ver `SECURITY.md` para pautas sobre credenciales
- Nunca pushear `.env` o `credentials/service_account.json`
- Cambios en Google Sheets API → tomar cuidado con breaking changes

## Reportar Bugs

Crear GitHub Issue con:
- Pasos para reproducir
- Comportamiento esperado vs observado
- Screenshots si aplica
