# Resume Project Description

## One-Line Description

Built SmartSupport AI, a full-stack customer-support platform with FastAPI, React, PostgreSQL, JWT/RBAC, SLA automation, knowledge-base workflows, analytics, notifications, and optional AI-powered retrieval.

## Resume Bullets

- Developed a full-stack customer-support workspace using FastAPI, React, TypeScript, SQLAlchemy, PostgreSQL, and Alembic, supporting ticket lifecycle management, agent assignment, internal notes, customer replies, analytics, and audit logging.
- Implemented JWT authentication and server-side role-based access control for administrators, senior agents, and support agents, including permission-gated ticket assignment and protected API workflows.
- Built priority-based SLA tracking for first response and resolution targets, including green, warning, breached, and transition-aware notification states.
- Integrated an OpenAI-compatible provider abstraction for ticket summaries, classification, draft replies, embeddings, similar-ticket search, and knowledge-base suggestions with explicit failure behavior when AI is unavailable.
- Implemented optional PostgreSQL pgvector retrieval with cosine similarity, embedding deduplication, HNSW indexes, and controlled degradation for environments without the optional AI substrate.
- Added Docker Compose deployment configuration, backend regression tests, frontend type checking, linting, production builds, and CI validation.

## Short Portfolio Version

SmartSupport AI is a production-oriented customer-support workspace that demonstrates secure API design, relational modeling, workflow automation, semantic retrieval, and full-stack integration. It uses FastAPI and PostgreSQL on the backend, React and TypeScript on the frontend, and an optional OpenAI-compatible AI layer.
