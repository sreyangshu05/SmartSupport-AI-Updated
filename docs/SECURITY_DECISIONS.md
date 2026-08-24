# Security Decisions

## Backend Authorization

Permissions are checked at the API boundary because frontend-only authorization can be bypassed by a direct request.

## Password Storage

Passwords are stored as bcrypt hashes rather than plaintext credentials.

## Token-Based Sessions

JWT access tokens allow the API to validate authenticated requests without storing session state in the frontend.

## Rate Limiting

Auth endpoints receive stricter protection against brute-force attempts, while general requests use a separate configurable limit.

## Explicit AI Failure

When provider credentials are unavailable, AI endpoints return an error instead of generating an unverified response. This preserves trust and makes operational failures visible.

## Prompt Boundaries

Customer and ticket text is untrusted input. Provider prompts separate application instructions from user content to reduce prompt-injection risk.

## Secret Handling

Development configuration is stored locally in `.env`; production secrets must be injected by the deployment environment or secret manager.
