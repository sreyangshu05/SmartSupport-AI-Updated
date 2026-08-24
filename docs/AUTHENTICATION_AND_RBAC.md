# Authentication and RBAC

## Authentication Flow

1. A user submits credentials to the login endpoint.
2. The backend verifies the password hash.
3. The backend issues a JWT access token.
4. The frontend stores the token for the active session.
5. Protected requests include the token in the `Authorization` header.
6. FastAPI dependencies resolve and validate the current user.

## Authorization Flow

1. A route declares the required permission.
2. The permission dependency resolves the authenticated user.
3. The user's role permissions are checked on the server.
4. The request continues only when the permission is present.

Frontend visibility is a convenience only; it is not the security boundary.

## Roles

- `admin`: administrative, analytics, audit, agent, ticket, and knowledge-base operations.
- `senior_agent`: support operations and assignment responsibilities.
- `agent`: support work within assigned permissions.

The exact permission matrix is defined in `backend/app/auth/permissions.py` and should be treated as the source of truth.

## Security Controls

- Password hashing with bcrypt.
- JWT signing with a configurable secret.
- Server-side permission checks.
- Active-user validation.
- Configurable rate limiting.
- CORS allowlist configuration.
- Audit logging.
- Environment-based secrets.
