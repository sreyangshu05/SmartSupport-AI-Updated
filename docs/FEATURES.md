# Features

## Authentication

- User registration and login.
- JWT access tokens.
- Token persistence and restoration in the frontend.
- Active-user checks on protected API requests.

## Role-Based Access Control

The backend enforces permissions through dependencies rather than relying on frontend visibility.

- Admin: broad operational and management access.
- Senior agent: support operations and assignment capabilities.
- Agent: support operations within assigned permissions.

## Ticket Management

- Create and view tickets.
- Filter tickets by status, priority, assignment, and other supported fields.
- Assign and reassign tickets.
- Add customer replies and internal notes.
- Enforce guarded lifecycle transitions.
- Track first response, resolution, closure, duplicate relationships, and audit events.

## SLA Tracking

- Priority-based first-response and resolution targets.
- Green, warning, and breached states.
- Due-date calculation.
- Transition-aware notification behavior.
- On-demand sweep support for open tickets.

## Knowledge Base

- Create and edit articles.
- Draft, review, approve, and publish content.
- Maintain article versions.
- Record views and helpfulness feedback.
- Associate articles with categories and tags.
- Retrieve relevant content for ticket assistance.

## AI Assistance

- Ticket summaries.
- Ticket classification.
- Draft replies.
- Similar-ticket retrieval.
- Knowledge-base suggestions.
- Optional embeddings and vector similarity search.
- Explicit unavailable responses when AI is not configured.

## Notifications and Analytics

- Notifications for ticket creation, assignment, replies, internal notes, and SLA degradation.
- Ticket, agent, SLA, and knowledge-base analytics.
- Audit records for important support actions.

## Operational Controls

- Configurable in-memory sliding-window rate limiting.
- CORS configuration.
- Environment-based settings.
- Database migrations.
- Seed data for local demonstration.
