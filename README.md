# SmartSupport AI

A full-stack customer-support workspace with PostgreSQL persistence, JWT authentication, server-side RBAC, ticket lifecycle controls, knowledge-base workflows, analytics, audit logging, and an optional OpenAI-compatible AI provider.

## What is real

- FastAPI backend with Alembic migrations and PostgreSQL persistence.
- JWT login and server-enforced permissions for admins, senior agents, and agents.
- Ticket creation, assignment, guarded state transitions, customer replies, internal notes, SLA state, events, and audit records.
- Knowledge-base draft/review/approved/published lifecycle, versions, feedback, and view statistics.
- SLA tracking with priority-based first-response and resolution targets, live green/warning/breached state, and admin notifications on degradation.
- In-app notifications on ticket creation, assignment, replies, and internal notes.
- In-memory sliding-window rate limiting on auth and API endpoints (configurable via `RATE_LIMIT_ENABLED`).
- Optional semantic search: when pgvector and an AI embedding provider are configured, ticket similarity and KB retrieval use cosine vector search; otherwise they fall back to keyword matching. No synthetic results either way.
- React/Vite frontend authenticated against the backend. There is no mock state or simulated AI in the shipped frontend.
- AI endpoints use an OpenAI-compatible configuration. If no provider key is configured, they return an explicit `503 AI is not configured`; they do not fabricate results.

## Local run with Docker Compose

1. Copy `.env.example` to `.env` and change `SECRET_KEY` and database password.
2. For local demo data, keep `SEED_DATA=true` and change the seeded password before any shared environment.
3. Run:

```bash
docker compose up --build
```

Open the frontend at `http://localhost:8080`. The API is proxied under `/api`; FastAPI docs are at `http://localhost:8001/docs`.

The initial local-only demo account is `admin@smart.support` / `admin123` unless changed in `.env`.

## Local development without Docker

Prerequisites: PostgreSQL 17 (with [pgvector](https://github.com/pgvector/pgvector) for semantic search), Redis 7, Python 3.13, Node 22.

```bash
# backend
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt pytest
cp ../.env.example .env
# adjust DATABASE_URL and REDIS_URL for host services
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8001

# separate terminal, frontend
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8001` in development.

## Deploying to Render, Railway, or Vercel

The recommended split deployment is FastAPI on Render or Railway and the Vite
frontend on Vercel or Render Static Site.

### Render

The repository includes `render.yaml`. In Render, choose **New > Blueprint**
and select the repository. The blueprint creates the API, PostgreSQL, Redis,
and frontend services. Set these values in the dashboard after creation:

- Backend `CORS_ORIGINS`: the deployed frontend URL.
- Backend `FRONTEND_URL`: the deployed frontend URL.
- Backend `AI_API_KEY`: only when AI is intentionally enabled.
- Frontend `VITE_API_BASE_URL`: the backend URL followed by `/api`.

Keep `SEED_DATA=false` for a shared or production environment.

### Railway backend

Create a Railway project with PostgreSQL and Redis plugins, then deploy the
`backend` directory as a Docker service. The backend includes
`backend/railway.json` and honors Railway's injected `PORT`. Add the variables
shown in `backend/.env.railway.example`, using Railway's generated database
and Redis connection variables.

### Vercel frontend

Create a Vercel project with `frontend` as the **Root Directory**. Vercel will
use `frontend/vercel.json` for SPA routing. Set:

```dotenv
VITE_API_BASE_URL=https://your-backend-domain.example/api
```

Then add that Vercel URL to the backend `CORS_ORIGINS` and `FRONTEND_URL`.

Never commit `.env` files or provider keys. Rotate any key that has been
exposed in a local file before deploying.

## AI provider configuration

Set these in `.env` or your deployment secret store:

```dotenv
AI_ENABLED=true
AI_PROVIDER=openai_compat
AI_BASE_URL=https://openrouter.ai/api/v1
AI_API_KEY=your-openrouter-api-key
AI_CHAT_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
AI_EMBEDDING_MODEL=text-embedding-3-small
```

OpenRouter is OpenAI-compatible, so the backend can use it without code changes. If you want to use the same provider settings in a Python playground, set `base_url="https://openrouter.ai/api/v1"` and pass your OpenRouter key. Do not put production secrets in Git.

## Validation

```bash
cd backend && python -m pytest
cd ../frontend && npm run typecheck && npm run build
```

GitHub Actions runs both backend tests and frontend typecheck/build on pull requests and pushes to `main`.

## Security notes

- Replace all defaults before production, especially `SECRET_KEY`, database credentials, and seeded admin credentials.
- Configure restrictive `CORS_ORIGINS` and `FRONTEND_URL`.
- Run behind TLS via your reverse proxy or platform.
- AI is optional. No key means no AI operation, not fake output.
