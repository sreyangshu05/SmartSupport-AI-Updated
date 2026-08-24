# SmartSupport AI

## Overview

SmartSupport AI is a full-stack customer-support workspace for managing tickets, agents, knowledge-base content, service-level agreements, notifications, analytics, audit history, and optional AI-assisted support workflows.

## Problem

Support teams need one place to manage customer conversations, assign work, track deadlines, reuse approved answers, and understand operational performance. The system combines those workflows behind authenticated, role-aware APIs and a React workspace.

## Solution

The application provides:

- JWT authentication and server-side role-based access control.
- Ticket creation, assignment, replies, internal notes, status transitions, and audit events.
- Priority-based SLA tracking with warning and breach states.
- Knowledge-base authoring, review, approval, publishing, versions, feedback, and usage statistics.
- Analytics and in-app notifications.
- Optional OpenAI-compatible chat and embedding providers.
- pgvector-backed retrieval when the database extension and embedding provider are available.
- Keyword or empty-result degradation when optional AI infrastructure is unavailable.

## Technology Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, Lucide React.
- Backend: Python, FastAPI, SQLAlchemy 2, Pydantic Settings.
- Persistence: PostgreSQL and Alembic migrations.
- Optional infrastructure: Redis and PostgreSQL pgvector.
- AI: OpenAI-compatible chat and embedding APIs.
- Deployment: Docker Compose, Nginx, and separate frontend/backend containers.

## Primary Users

- Administrators manage users, permissions, policies, audit data, and operational settings.
- Senior agents handle support work and assignment workflows.
- Agents work assigned tickets and contribute support content.

## Project Status

This is a development-ready portfolio project. The repository contains implemented backend and frontend workflows, tests, migrations, container definitions, and CI configuration. Production traffic, hosted infrastructure, AI quality metrics, and full browser E2E coverage are not claimed.
