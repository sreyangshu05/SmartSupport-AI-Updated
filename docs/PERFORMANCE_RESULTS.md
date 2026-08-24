# Performance Results

## Verified Results

The repository includes automated tests for backend behavior, including authentication, tickets, knowledge-base workflows, RBAC, security controls, SLA sweeps, and vector-store behavior.

Frontend validation is defined through TypeScript type checking, ESLint, and the Vite production build.

## Metrics Not Yet Established

No production performance numbers are claimed for:

- Requests per second.
- p95 or p99 API latency.
- Database query latency at scale.
- Vector-search latency.
- AI provider latency.
- Concurrent users.
- Memory or CPU utilization.

## Benchmark Plan

1. Generate representative users, tickets, articles, notifications, and embeddings.
2. Measure authentication, ticket listing, ticket creation, analytics, and retrieval separately.
3. Record p50, p95, and p99 latency with database and provider timings.
4. Repeat with AI disabled, keyword retrieval, and pgvector retrieval.
5. Test rate limiting and failure recovery under concurrent load.
6. Record environment details with every benchmark result.
