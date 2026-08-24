# Frontend Architecture

## Structure

```text
frontend/src/
├── components/       workspace screens, lists, forms, and modals
├── context/          authenticated application state
├── lib/              API client helpers
├── types/            shared frontend response and domain types
├── App.tsx           application composition
├── main.tsx          browser entry point
└── index.css         global styling
```

## Runtime Flow

1. Vite serves the React application during development.
2. `AppContext` stores the current user, token, tickets, knowledge-base data, notifications, and dashboard state.
3. The API client sends authenticated requests to the backend.
4. Components render the workspace and invoke API operations through the shared application state.
5. Vite proxies `/api` to `http://127.0.0.1:8001` during local development.

## UI Areas

- Dashboard and analytics.
- Ticket list and ticket detail workflow.
- Knowledge-base browsing, article details, and article creation.
- Agent administration.
- Notifications and authenticated workspace navigation.

## Design Approach

The frontend is an operational workspace rather than a marketing page. It prioritizes fast scanning, clear ticket state, role-aware actions, modal-based detail workflows, and direct feedback from API operations.

## Validation

Frontend validation is provided through TypeScript type checking, ESLint, and the Vite production build.
