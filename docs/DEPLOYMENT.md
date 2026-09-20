# Deployment

A low-cost layout is a static/Node frontend on Vercel, a continuously running FastAPI worker/API on Render, Fly.io, Railway, or similar, and Supabase PostgreSQL. Free tiers and sleep policies change; verify current pricing before selection. Scheduled outreach requires the backend and worker to remain awake, which often requires a paid tier. Do not create paid resources automatically.

The embedded worker is suitable for one backend replica. For multiple replicas, separate the worker role and add PostgreSQL row-level claiming before scaling. Configure a persistent database volume; never use an ephemeral SQLite file in production.

Back up PostgreSQL daily with provider snapshots plus periodic `pg_dump`; test restores into a separate database. Monitor `/health`, `/ready`, job failures, Gmail errors, bounce rate, and sending pauses. Alert on any kill-switch transition or repeated provider failure.
