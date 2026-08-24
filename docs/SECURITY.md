# Security

## Controls Implemented

- Bcrypt password hashing.
- JWT authentication.
- Server-side role and permission enforcement.
- Active-user validation.
- In-memory sliding-window rate limiting.
- Configurable CORS origins.
- Audit logging for important actions.
- Environment-based configuration and secrets.
- Explicit failure for unavailable AI configuration.
- Prompt boundaries for untrusted ticket content.

## Rate Limiting

Auth paths have stricter limits than general API traffic. The limiter can be configured with `RATE_LIMIT_ENABLED` and is disabled automatically in the test environment so tests are deterministic.

## Secret Management

Never commit real values for:

- `SECRET_KEY`.
- `POSTGRES_PASSWORD`.
- `AI_API_KEY`.
- Production database URLs.

Use local `.env` files only for development and use a deployment secret store for shared environments.

## Production Requirements

- Replace all development credentials.
- Use a strong, unique signing key.
- Restrict CORS origins.
- Run behind TLS.
- Use managed secrets and database credentials.
- Review provider data handling before enabling AI.
- Replace the in-memory limiter with a shared solution when running multiple API instances.

## Security Testing

The backend test suite covers authentication, permission boundaries, rate limiting, prompt safety controls, and ownership-sensitive behavior. A production security review and penetration test remain separate activities.
