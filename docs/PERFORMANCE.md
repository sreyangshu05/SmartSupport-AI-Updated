# Performance

## Current Design

- PostgreSQL indexes support common ticket, article, notification, and audit lookups.
- pgvector HNSW indexes support cosine-oriented embedding search when enabled.
- SQLAlchemy connection pooling is configured in the backend.
- Rate limiting prevents uncontrolled request bursts.
- AI retries and timeouts are configurable.

## Performance-Sensitive Areas

- Ticket and analytics aggregation queries.
- Embedding generation latency.
- Vector similarity search.
- Large knowledge-base retrieval.
- Notification and audit volume.
- In-memory rate limiting across multiple API workers.

## Scaling Considerations

- Replace in-memory rate limiting with a shared store for multiple backend instances.
- Run scheduled SLA sweeps through a worker or external scheduler.
- Use managed PostgreSQL and Redis for production workloads.
- Add pagination and query-specific indexes as data volume grows.
- Monitor AI provider latency, retries, failures, and token usage.

## Measurement Status

The repository does not claim production throughput, latency percentiles, benchmark results, or capacity limits. Those values require a controlled benchmark environment and representative data.
