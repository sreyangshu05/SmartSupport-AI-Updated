# Engineering Challenges

## Keeping Authorization Correct

The frontend needs role-aware controls, but permissions must remain authoritative in the backend. The solution uses explicit permission dependencies on protected routes.

## Modeling Ticket State

Support tickets have guarded transitions, replies, internal notes, assignments, resolution state, and audit effects. These rules belong in the service layer so every caller receives the same behavior.

## Tracking SLA Degradation

It is not enough to calculate the current SLA state. The system must detect transitions into warning or breach states to avoid sending duplicate notifications.

## Making AI Optional

AI provider failures must not turn into fabricated answers. The implementation reports missing configuration explicitly and keeps non-AI workflows available.

## Adding Semantic Retrieval Safely

Vector search depends on both provider embeddings and database support. The vector store isolates those dependencies and supports controlled degradation when the optional substrate is unavailable.

## Keeping Frontend Types Aligned

The frontend consumes real API payloads. Shared type definitions and type checking help expose drift between backend schemas and UI assumptions.
