# Architecture

The FastAPI service owns authentication, policy, persistence, provider status, and all state changes. SQLAlchemy models cover discovery campaigns, campaign prospects, persistent jobs, companies, contacts, contact-source provenance, drafts, Gmail connection state, activity, and agent controls. The Next.js dashboard is an authenticated API client; no secrets are shipped to it.

Draft delivery is a state machine: contact → sourced → verified → drafted → validated → approved → eligible → queued/sent. Suppression, kill switch, pause state, agent mode, verification, idempotency, and global limits are checked at the final send boundary. Production should use PostgreSQL and a database-backed worker claiming queue rows with `FOR UPDATE SKIP LOCKED`.

The embedded worker claims persistent rows, recovers stale ten-minute locks, retries with exponential backoff, and uses unique deduplication keys. Production deployments should run exactly one worker with SQLite or use PostgreSQL row locks for horizontal workers.

Brave Search supplies candidate company websites. Official-site research checks a limited set of public pages using a descriptive user agent, follows no authentication, and accepts only same-domain, role-relevant emails. Search snippets remain attributed evidence, not proof of company behavior. Rule-based draft generation and explicit mock sending work without paid AI.
