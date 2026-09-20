# GiftReach AI

Responsible, single-owner corporate gifting outreach for Bengaluru and Karnataka. The MVP records source provenance, supports multiple contacts per company, generates policy-checked drafts, and defaults to a non-delivering mock provider.

## Run locally

1. Copy `.env.example` to `.env`, set a long `APP_SECRET`, owner email, and strong password.
2. Backend: `cd backend`, create a virtual environment, run `pip install -r requirements.txt`, then `uvicorn app.main:app --reload`.
3. Frontend: `cd frontend`, run `npm install`, then `npm run dev`.
4. Open `http://localhost:3000`. API docs are at `http://localhost:8000/docs`.

No real email is sent without an implemented and connected Gmail provider. The current send provider is explicitly labelled mock. Controlled autopilot, recipient verification, approved drafts, and unpaused sending are all required even for mock sends.

## Verify

```text
cd backend && pytest
cd frontend && npm run typecheck && npm run lint && npm run build
```

See [setup](docs/SETUP.md), [architecture](docs/ARCHITECTURE.md), and [security](docs/SECURITY.md).

