# Contributing

## Development Setup

Follow the setup instructions in `README.md`. For local work, run the backend and frontend in separate terminals.

## Before Opening a Change

- Read the relevant architecture and security documentation.
- Keep business rules in backend services.
- Keep authorization checks on the backend.
- Avoid fabricated AI output or mock production behavior.
- Add or update focused tests for behavior changes.
- Update documentation when configuration or workflows change.

## Validation

```powershell
cd backend
python -m pytest

cd ..\frontend
npm run typecheck
npm run lint
npm run build
```

## Pull Requests

Describe:

- The problem being solved.
- The implementation and affected components.
- Tests that were run.
- Configuration or migration changes.
- Known limitations or follow-up work.

Do not include API keys, passwords, customer data, or generated secrets in commits.
