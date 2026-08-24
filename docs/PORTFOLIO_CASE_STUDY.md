# SmartSupport AI: Portfolio Case Study

## Project Summary

SmartSupport AI is a full-stack customer-support workspace that combines ticket operations, knowledge management, SLA tracking, analytics, audit logging, and optional AI assistance in one authenticated application.

## The Problem

Support teams often work across disconnected tools. This makes it harder to assign ownership, track response deadlines, reuse approved answers, and maintain an auditable history of customer interactions.

## What I Built

- A FastAPI backend with PostgreSQL persistence and Alembic migrations.
- A React and TypeScript workspace for tickets, agents, analytics, notifications, and knowledge-base workflows.
- JWT authentication and server-enforced RBAC for admins and support agents.
- Priority-based SLA tracking with warning, breach, and notification behavior.
- An OpenAI-compatible provider abstraction for summaries, classification, draft replies, and embeddings.
- pgvector-backed semantic retrieval with explicit degradation when optional infrastructure is unavailable.
- Docker Compose configuration and automated backend/frontend validation.

## Technical Highlights

The most important design decision was keeping AI optional and evidence-based. Without valid provider configuration, the system returns an explicit unavailable response rather than producing synthetic content. Likewise, semantic search uses real embeddings and vector similarity when the required database and provider capabilities exist.

## Engineering Challenges

The project required coordinating authorization, lifecycle rules, database relationships, SLA transitions, notification ownership, AI failure behavior, and frontend API types without placing business logic in the UI.

## Result

The repository provides a realistic support workflow with persisted data, auditable actions, configurable infrastructure, automated tests, and clear boundaries between core functionality and optional AI capabilities.

## Honest Scope

The project is development-ready. Production traffic, hosted deployment, AI quality metrics, load benchmarks, and complete browser E2E coverage remain outside the verified scope.
