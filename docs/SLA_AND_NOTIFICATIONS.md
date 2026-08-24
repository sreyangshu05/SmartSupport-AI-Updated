# SLA and Notifications

## SLA Model

Each ticket can have separate tracking for:

- First response.
- Resolution.

Policies define target and warning windows by ticket priority. The service calculates due times and evaluates the current state as green, warning, or breached.

## State Evaluation

SLA evaluation compares the current time with the configured target and warning thresholds. Notifications are generated on meaningful degradation transitions rather than repeatedly for an unchanged state.

## Notification Events

Notifications can be created when:

- A ticket is created.
- A ticket is assigned or reassigned.
- A customer reply is added.
- An internal note is added.
- An SLA moves into a degraded state.

The service avoids notifying the actor about their own action when appropriate.

## Sweep Behavior

`SLAService.sweep_expired()` evaluates open tickets on demand. A deployment can invoke that operation from a scheduled worker or job. The repository includes the service behavior; scheduling is deployment-specific.

## Data Consistency

Notification creation joins the caller's transaction so the event and its notification are committed consistently with the originating operation.
