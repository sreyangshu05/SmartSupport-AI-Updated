# Environment Configuration

Copy `.env.example` to `.env` and adjust values for the selected environment.

## Core Settings

| Variable | Purpose |
|---|---|
| `ENV` | Runtime environment such as development, test, staging, or production |
| `SECRET_KEY` | JWT signing secret |
| `CORS_ORIGINS` | Comma-separated browser origins |
| `FRONTEND_URL` | Public frontend origin |

## Database and Redis

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection URL |
| `REDIS_URL` | Redis connection URL |
| `REDIS_ENABLED` | Enables or disables Redis integration |

## AI

| Variable | Purpose |
|---|---|
| `AI_ENABLED` | Enables AI operations |
| `AI_PROVIDER` | Provider implementation name |
| `AI_BASE_URL` | OpenAI-compatible API base URL |
| `AI_API_KEY` | Provider credential |
| `AI_CHAT_MODEL` | Chat model identifier |
| `AI_EMBEDDING_MODEL` | Embedding model identifier |

## Seed Data

| Variable | Purpose |
|---|---|
| `SEED_DATA` | Enables local demo seeding |
| `SEED_ADMIN_EMAIL` | Seed admin email |
| `SEED_ADMIN_PASSWORD` | Seed admin password |

## Local Defaults

For local development, PostgreSQL is expected on port `5432`, Redis on port `6379`, FastAPI on port `8001`, and Vite on port `5173`. Do not reuse development defaults in production.
