# API Documentation

## API Base URL

- Local backend: `http://localhost:8001`
- Local frontend proxy: `/api`
- Interactive OpenAPI documentation: `http://localhost:8001/docs`

## API Groups

| Group | Purpose |
|---|---|
| Auth | Registration, login, and current-user access |
| Tickets | Ticket CRUD, assignment, replies, notes, transitions, and AI helpers |
| Knowledge base | Article lifecycle, versions, feedback, views, and retrieval |
| Agents | Agent administration and support profile fields |
| Analytics | Operational and support metrics |
| Notifications | User notification listing and read state |
| Audit | Audit log access |
| Health | Service health checks |
| Miscellaneous | Supporting application endpoints |

## Authentication

Protected requests use a bearer token:

```http
Authorization: Bearer <access-token>
```

The frontend obtains the token from the login response and includes it on protected requests.

## API Behavior

- Request bodies and responses are validated with Pydantic schemas.
- Permission dependencies enforce authorization at the route boundary.
- Missing resources return not-found errors.
- Invalid state transitions return validation or conflict errors.
- Rate-limited requests return HTTP 429 with a `Retry-After` header.
- AI operations return HTTP 503 when configured provider credentials are unavailable.

The generated OpenAPI document at `/openapi.json` is the authoritative endpoint contract.
