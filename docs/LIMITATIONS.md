# Limitations

- The project is development-ready, not production-verified.
- Hosted deployment and real customer traffic have not been claimed.
- AI response quality and embedding quality have not been benchmarked.
- Browser-based end-to-end coverage is not complete.
- The in-memory rate limiter is not suitable as the sole limiter for multiple API instances.
- SLA scheduling requires an external worker, cron job, or platform scheduler.
- AI features require a valid OpenAI-compatible provider configuration.
- Semantic retrieval requires PostgreSQL pgvector and compatible embedding dimensions.
- Default seed credentials are for local demonstration only.
- Observability, alerting, backup recovery, and disaster-recovery procedures require deployment-specific configuration.
