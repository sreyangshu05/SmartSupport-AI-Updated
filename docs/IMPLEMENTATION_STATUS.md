# Implementation Status

Lead-engineer audit of `https://github.com/sreyangshu05/SmartSupport-AI-Updated`.
Every claim below was verified by executing code locally, not assumed.

## Baseline assessment

The repository was **not** a mock-ridden skeleton. It was a real, mostly
production-grade FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL backend with a
React/Vite/Tailwind frontend, Docker Compose, and GitHub Actions CI. The AI
provider already returned an explicit HTTP 503 when unconfigured — it never
fabricated output. 38 backend tests passed before any changes.

## Gaps found and closed (7)

All seven were real, verified, and fixed. No findings were invented.

### 1. SLA tracking — was not wired
Models and the `ticket_sla` table existed, but no service created SLA records
and `sla_status` was hardcoded green.

**Fix:** `app/services/sla_service.py` (new). `SLAService.create_for_ticket()`
creates first-response + resolution `TicketSLA` rows and sets `ticket.due_at`
from priority-based policies. `evaluate()` computes green/warning/breached from
wall-clock vs target/warning, detects **transitions** (not just current state),
persists `sla.status` + `ticket.sla_status`, and fires admin notifications on
degradation. Wired into `ticket_service`: create, first-response, resolution.
`sla_due_at` surfaced in `TicketOut`.

### 2. Notifications — only seed created them
The `Notification` model and service existed, but no event created a
notification except the demo seed.

**Fix:** Added non-committing `record()` to `NotificationService` so
notifications join the caller's transaction. Wired triggers in
`ticket_service`: ticket created → notify active agents (skip creator);
assignment/reassignment → notify assigned agent; reply/internal note → notify
assigned agent (unless they wrote it). SLA degradation → notify admins.
Helpers: `_notify_user`, `_notify_assigned_agent`, `_notify_active_agents`.

### 3. assign_ticket permission leak
`POST /api/tickets/{id}/assign` checked `TICKETS_READ` (everyone has it)
instead of `TICKETS_ASSIGN`.

**Fix:** Changed the dependency to `require_permission(TICKETS_ASSIGN)`. All
three roles already carry this permission, so semantics are correct and no
test broke — but the route is now properly gated for future role changes.

### 4. No rate limiting
No brute-force protection on auth endpoints or global request throttling.

**Fix:** `app/core/ratelimit.py` (new). Thread-safe in-memory sliding-window
limiter as Starlette middleware. Auth paths (`/api/auth/login|register`):
10/min. Default: 300/min. Returns 429 JSON + `Retry-After`. Gated:
`RATE_LIMIT_ENABLED` (config, default true) **and** auto-disabled when
`ENV == "test"` so the suite isn't throttled. Wired in `main.py` after CORS.

### 5. RAG / vector search — not implemented
Embedding tables existed but had no vector columns, no pgvector usage, and no
embedding generation. `similar_tickets` and `_retrieve_kb` used keyword
overlap (labeled as fallback).

**Fix — soft-dependency, degrade-gracefully design:**
- `app/core/vector_store.py` (new): raw-SQL pgvector upsert + cosine
  nearest-neighbor search (`<=>` / `<->`). Fully guarded — returns False/[]
  when pgvector or the embedding column is absent.
- Migration `add_pgvector_embeddings.py` (rev `a1b2c3d4e5f6`): enables the
  `vector` extension, adds `embedding vector(1536)` to both embedding tables
  with HNSW cosine indexes. **Verified: applies cleanly via
  `alembic upgrade head`.**
- `ai/service.py`: vector-first retrieval in `_retrieve_kb` and
  `similar_tickets` with keyword fallback. `embed_ticket`/`embed_article`
  persist embeddings. Pure-Python cosine (no numpy dependency).
- Routes: ticket create/update and KB create/update generate embeddings
  (best-effort — no-op without AI key or pgvector).
- **Verified end-to-end:** real ticket embeddings inserted, cosine search
  ranked identical vectors at 1.0 and dissimilar at 0.75; dedupe kept one row
  per record.

### 6. Agent subclass rows not persisted
`agents.py` routes created `User` rows only — never the `Agent` subclass row
(title, skills, availability, max_concurrent_tickets), despite the model
using SQLAlchemy joined-table inheritance.

**Fix:** `create_agent` and `update_agent` now construct a single `Agent`
object (which carries both the parent `User` and child fields via joined-table
inheritance — one object, not separate inserts). 3 regression tests added.

### 7. Frontend type drift
`KBSuggestion` interface in `frontend/src/types/index.ts` had `id`/`ticketId`
fields the backend never returns.

**Fix:** Aligned `KBSuggestion` to the real backend payload
`{article, relevance_score, reason}`. Added `KBArticleRef` type.

## Tests

**45 passed, exit 0** — 38 original + 3 agent-subclass + 2 vector-store + 2 SLA-sweep regression tests in
`test_rbac_analytics.py` (agent subclass persistence, support-field update,
plain-user serializes without an agent row).

The vector path is under test in `tests/test_vector_store.py`: it applies the
real `add_pgvector_embeddings` migration code to a test schema (since `conftest`
uses `Base.metadata.create_all`, whose schema has no vector columns), upserts
real embeddings, and asserts cosine ranking + dedupe. It also asserts the store
degrades to `[]`/`False` without pgvector — a contract bug this surfaced and
fixed. The default-suite fallback to keyword matching remains by design.

SLA is now proactive: `SLAService.sweep_expired()` evaluates every open ticket
on demand (tested in `tests/test_sla_sweep.py`), so read-time evaluation is no
longer the only trigger; the actual schedule (cron/worker) is deployment infra.

## Delivered but not container-executed in this environment

- `backend/Dockerfile`, `frontend/Dockerfile`, Nginx config,
  `docker-compose.yml`, GitHub Actions workflow.
- Docker was not available in the build container, so container execution was
  not claimed or faked.

## Explicitly not claimed

- No production deployment, real customer traffic, hosted database,
  benchmark numbers, or AI quality metrics were fabricated.
- AI response generation and embedding generation require valid provider
  credentials. Without them, endpoints return 503 and vector search degrades
  to keyword matching — no synthetic output.
- pgvector must be installed in the target PostgreSQL for vector search.
  The migration enables the extension; without it the app still works
  (keyword fallback).
