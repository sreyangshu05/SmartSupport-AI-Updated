# Demo Script

## Start the Application

```powershell
# Terminal 1
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8001

# Terminal 2
cd frontend
npm run dev
```

Open `http://localhost:5173`.

## Demonstration Flow

1. Log in with the seeded admin account.
2. Open the dashboard and show ticket, SLA, and knowledge-base metrics.
3. Create a ticket with a priority and category.
4. Assign the ticket to an agent.
5. Add a customer reply and an internal note.
6. Show the ticket status, due date, audit activity, and notifications.
7. Open the knowledge base and create or review an article.
8. Publish an approved article and demonstrate its feedback or usage data.
9. Open analytics to show operational aggregation.
10. Demonstrate AI only when a valid provider configuration is enabled.

## AI Demo Note

When AI is disabled, show the explicit unavailable response as a reliability and transparency behavior. Do not present seeded or fabricated AI output as a provider result.

## Portfolio Talking Points

- Why authorization is enforced on the backend.
- How SLA transitions avoid duplicate notifications.
- How optional AI failure is handled.
- Why pgvector is isolated behind a vector-store abstraction.
- How migrations and tests protect the data model.
