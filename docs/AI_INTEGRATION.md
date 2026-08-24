# AI Integration

## Provider Model

The backend uses an OpenAI-compatible provider abstraction. Provider details are configured through environment variables, so compatible hosted or self-hosted endpoints can be used without changing application routes.

## Supported Workflows

- Ticket summarization.
- Ticket classification.
- Draft reply generation.
- Similar-ticket lookup.
- Knowledge-base suggestions.
- Text embeddings for retrieval.

## Configuration

```dotenv
AI_ENABLED=true
AI_PROVIDER=openai_compat
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=your-provider-key
AI_CHAT_MODEL=gpt-4o-mini
AI_EMBEDDING_MODEL=text-embedding-3-small
```

## Failure Behavior

AI is optional. Without a valid provider key, AI endpoints return an explicit `503 AI is not configured`. The system does not fabricate summaries, classifications, replies, or retrieval results.

## Request Safety

Ticket and customer text is treated as untrusted input. Prompt construction keeps application instructions separate from user-provided content and records generation metadata such as model, status, latency, and errors.

## Operational Considerations

- Keep provider keys in environment variables or a secret manager.
- Set timeouts and retry limits appropriate to the provider.
- Monitor provider failures and latency.
- Do not send production customer data to a provider without an approved data-handling policy.
