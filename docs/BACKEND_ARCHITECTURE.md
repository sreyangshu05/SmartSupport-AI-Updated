# Backend Architecture

## Layers

```text
backend/app/
├── api/routes/       HTTP endpoints and request dependencies
├── auth/             authentication, security, and permissions
├── ai/               provider abstraction and AI orchestration
├── core/             configuration, database, rate limiting, vector store
├── models/           SQLAlchemy entities and enums
├── schemas/          Pydantic request and response models
├── services/         domain workflows and business rules
└── workers/          background-work extension point
```

## Route Layer

Routes validate requests, obtain the database session, resolve the current user, enforce permissions, and delegate work. They are grouped by authentication, tickets, knowledge base, agents, analytics, notifications, audit, health, and miscellaneous operations.

## Service Layer

Services own reusable business behavior, including ticket lifecycle rules, SLA evaluation, notification creation, audit recording, authentication operations, knowledge-base workflows, and analytics aggregation.

## Persistence

SQLAlchemy uses PostgreSQL through the configured `DATABASE_URL`. Alembic migrations create and evolve the schema. Sessions are provided to routes through the database dependency.

## Configuration

`pydantic-settings` reads `.env` and environment variables. The configuration covers database access, Redis, CORS, security, rate limiting, AI providers, and demo seeding.

## Error Handling

The backend returns HTTP errors for invalid authentication, insufficient permissions, missing resources, invalid transitions, unavailable AI configuration, and rate-limit violations. AI operations return an explicit unavailable response rather than invented content when no provider key exists.
