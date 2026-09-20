# Architecture

The FastAPI service owns authentication, policy, persistence, provider status, and all state changes. SQLAlchemy models cover companies, contacts, contact-source provenance, campaigns, drafts, activity, and persistent agent controls. The Next.js dashboard is an authenticated API client; no secrets are shipped to it.

Draft delivery is a state machine: contact → sourced → verified → drafted → validated → approved → eligible → queued/sent. Suppression, kill switch, pause state, agent mode, verification, idempotency, and global limits are checked at the final send boundary. Production should use PostgreSQL and a database-backed worker claiming queue rows with `FOR UPDATE SKIP LOCKED`.

Provider boundaries are exposed through integration configuration. This MVP includes safe rule-based generation and mock sending. Search, verification, AI, and Gmail credentials remain optional and unavailable states are visible.

