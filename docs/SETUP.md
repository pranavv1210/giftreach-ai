# Setup

Requires Python 3.11+ and Node 20+. Copy `.env.example` to `.env`; never commit it. SQLite is suitable for local development. Set `DATABASE_URL` to a PostgreSQL URL for a hosted environment. The owner password is read only by the backend; use a unique long password and rotate the default before exposing the service.

The development UI expects the API at `http://localhost:8000`. Override `NEXT_PUBLIC_API_URL` at frontend build time when deploying. Set `FRONTEND_ORIGIN` to the exact dashboard origin so credentialed CORS remains restricted.

