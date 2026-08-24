# Troubleshooting

## `docker compose` Fails

- Confirm Docker Desktop is installed and running.
- Check that ports `8080` and `8001` are not already in use.
- Run `docker compose logs backend` or `docker compose logs postgres`.
- Rebuild after changing dependencies with `docker compose up --build`.

## Backend Cannot Connect to PostgreSQL

- Confirm PostgreSQL is running.
- Confirm the database and user exist.
- Check `DATABASE_URL`.
- Run migrations from the `backend` directory.

```powershell
alembic upgrade head
```

## Backend Cannot Connect to Redis

Redis is optional in the local configuration. Set:

```dotenv
REDIS_ENABLED=false
```

## AI Returns `503 AI is not configured`

Set `AI_ENABLED=true`, a valid `AI_API_KEY`, a compatible `AI_BASE_URL`, and valid model names. Restart the backend after changing `.env`.

## Frontend Cannot Reach the API

- Confirm FastAPI is running on port `8001`.
- Confirm Vite is running on port `5173`.
- Check that requests use `/api` so the Vite proxy can forward them.
- Inspect the browser network panel and backend logs.

## PowerShell Virtual Environment Error

Run once for the current Windows user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Missing Commands

Install dependencies before running validation:

```powershell
pip install -r backend\requirements.txt
cd frontend
npm ci
```
