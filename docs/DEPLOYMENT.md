# Deployment

A low-cost layout is a static/Node frontend on Vercel, a continuously running FastAPI worker/API on Render, Fly.io, Railway, or similar, and Supabase PostgreSQL. Free tiers and sleep policies change; verify current pricing before selection. Scheduled outreach requires the backend and worker to remain awake, which often requires a paid tier. Do not create paid resources automatically.

The embedded worker is suitable for one backend replica. For multiple replicas, separate the worker role and add PostgreSQL row-level claiming before scaling. Configure a persistent database volume; never use an ephemeral SQLite file in production.

## Recommended first deployment

- Frontend: Vercel, with the project root set to `frontend` and `NEXT_PUBLIC_API_URL` set to the public HTTPS backend URL.
- Backend: one always-on Render web service built from `backend/Dockerfile`, or an equivalent persistent container service.
- Database: Supabase PostgreSQL, configured through `DATABASE_URL`. Do not use SQLite on an ephemeral web service.

Backend production variables must include `ENVIRONMENT=production`, the exact Vercel URL in `FRONTEND_ORIGIN`, a PostgreSQL `DATABASE_URL`, owner credentials, app/token secrets, Gmail credentials, and a deployed Gmail redirect URI. Update the Google OAuth client redirect URI to `https://YOUR-BACKEND/api/integrations/gmail/callback`.

The free Render web service sleeps after inactivity and loses local filesystem state, so it is not suitable for continuous autonomous jobs or SQLite. Use an always-on service for scheduled discovery, or accept that jobs only run while the free service is awake.

Back up PostgreSQL daily with provider snapshots plus periodic `pg_dump`; test restores into a separate database. Monitor `/health`, `/ready`, job failures, Gmail errors, bounce rate, and sending pauses. Alert on any kill-switch transition or repeated provider failure.
