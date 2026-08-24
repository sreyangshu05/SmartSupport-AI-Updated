# Technical Decisions

## FastAPI

FastAPI provides typed request validation, dependency injection, OpenAPI generation, and a clear route boundary for an API-heavy support application.

## React and TypeScript

React supports a component-based operational workspace, while TypeScript helps keep API payloads and UI state aligned.

## PostgreSQL

PostgreSQL provides relational integrity for tickets, users, articles, notifications, audits, and SLA records. It also supports pgvector for optional semantic retrieval.

## SQLAlchemy and Alembic

SQLAlchemy separates domain persistence from route code, and Alembic provides repeatable schema evolution.

## JWT and Server-Side RBAC

JWT supports stateless authenticated API requests. Permission checks remain on the server so UI state cannot bypass authorization.

## Optional AI Provider

The provider abstraction keeps AI functionality replaceable and makes the core support workspace usable when AI is disabled or unavailable.

## Docker Compose

Compose provides a repeatable local stack containing the API, frontend, PostgreSQL, and Redis services.

## In-Memory Rate Limiting

An in-memory sliding-window limiter keeps the local implementation simple and dependency-light. A shared limiter is required when scaling the API horizontally.
