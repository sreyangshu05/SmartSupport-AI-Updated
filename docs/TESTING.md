# Testing

## Backend Tests

Backend tests are located under `backend/tests/` and cover:

- Authentication.
- Ticket operations.
- Knowledge-base workflows.
- RBAC and analytics.
- Security controls.
- SLA sweeps.
- Vector-store behavior.

Run them from the repository root:

```powershell
cd backend
python -m pytest
```

## Frontend Validation

```powershell
cd frontend
npm run typecheck
npm run lint
npm run build
```

## Test Strategy

- Unit-level tests verify service and utility behavior.
- API tests verify authenticated request flows and permission boundaries.
- Regression tests protect previously fixed defects.
- Migration-backed vector tests verify pgvector operations where supported.
- Type checking and production builds validate the frontend integration.

## Test Data

Local seed data is intended for demonstration only. Do not use the default seeded credentials in a shared or production environment.

## Remaining Coverage

Browser-based end-to-end tests, load testing, provider-quality evaluation, and production infrastructure tests should be added before a production launch.
