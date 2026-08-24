# Database Schema

## Database

The application uses PostgreSQL through SQLAlchemy and Alembic. The default local connection is:

```text
postgresql+psycopg2://smartuser:smartpass@localhost:5432/smartsupport
```

## Main Entities

| Entity | Responsibility |
|---|---|
| User | Identity, role, status, and account data |
| Agent | Support profile fields associated with a user |
| Role | Permission definitions |
| Ticket | Customer-support issue and lifecycle state |
| Customer | Customer identity and support metadata |
| Category | Ticket and article classification |
| SLA policy | Priority-based timing rules |
| Ticket SLA | Per-ticket first-response and resolution tracking |
| KB article | Support content and publication state |
| KB article version | Historical article content |
| KB article embedding | Optional vector representation for retrieval |
| Ticket embedding | Optional vector representation for similarity search |
| Notification | User-facing operational notification |
| Audit log | Immutable-style record of important actions |
| AI generation | AI request, output, model, latency, and status metadata |

## Migration Strategy

Run migrations from the `backend` directory:

```powershell
alembic upgrade head
```

The initial migration creates the relational schema. The pgvector migration adds vector columns and HNSW indexes. Environments that do not provide pgvector are expected to use the application's graceful degradation behavior, subject to the target database's migration capabilities.

## Data Integrity

- Foreign keys connect tickets, users, customers, categories, articles, and notifications.
- Unique indexes protect user email, ticket number, and role names.
- Delete behavior is defined for dependent records such as notifications, embeddings, and article versions.
- Service-layer rules protect lifecycle transitions and ownership-sensitive operations.
