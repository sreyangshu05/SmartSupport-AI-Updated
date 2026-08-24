# Deployment

## Docker Compose

The repository includes services for PostgreSQL, Redis, the FastAPI backend, and the Nginx-served frontend.

```powershell
docker compose up --build
```

Local endpoints:

- Frontend: `http://localhost:8080`
- Backend docs: `http://localhost:8001/docs`

Stop the stack with `Ctrl+C` or:

```powershell
docker compose down
```

## Render

Use the repository-root `render.yaml` as a Render Blueprint. It defines a
Docker web service for the backend, a static frontend, PostgreSQL, and Redis.
Set the frontend URL in the backend CORS variables and set the frontend
`VITE_API_BASE_URL` to the deployed backend URL ending in `/api`.

## Railway and Vercel

Deploy the `backend` directory as a Railway Docker service and provision
PostgreSQL and Redis in the Railway project. The service uses Railway's
injected `PORT` and health-check path `/api/health`.

Deploy the `frontend` directory as a Vercel project with `frontend` selected as
the root directory. Set `VITE_API_BASE_URL` to the public backend URL ending
in `/api`, then add the Vercel origin to backend CORS configuration.

## Service Responsibilities

- PostgreSQL stores application data.
- Redis provides optional external service support.
- Backend exposes the API on container port `8000` and host port `8001`.
- Frontend serves the compiled application on container port `80` and host port `8080`.

## Deployment Checklist

- Set a strong `SECRET_KEY`.
- Set a non-default database password.
- Restrict `CORS_ORIGINS` and `FRONTEND_URL`.
- Configure a production database and Redis service.
- Run `alembic upgrade head`.
- Decide whether AI and pgvector are enabled.
- Change seeded credentials or disable seeding.
- Put TLS in front of the application.
- Configure logs, health checks, backups, and monitoring.

## CI

GitHub Actions runs backend tests and frontend typecheck/build checks on pull requests and pushes to `main`.

## Production Status

The repository contains deployment configuration, but hosted deployment, real traffic, scaling, backup recovery, and production observability are not claimed as verified.
