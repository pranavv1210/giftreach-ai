# GiftReach AI

Responsible, single-owner corporate gifting outreach for Bengaluru and Karnataka. Create a discovery campaign in the dashboard and the persistent worker searches through Brave, researches official company sites, preserves contact provenance, scores prospects, and prepares policy-checked drafts for bulk review.

## Run locally

1. Copy `.env.example` to `.env`, set a long `APP_SECRET`, owner email, and strong password.
2. Backend: `cd backend`, create a virtual environment, run `pip install -r requirements.txt`, then `uvicorn app.main:app --reload`.
3. Frontend: `cd frontend`, run `npm install`, then `npm run dev`.
4. Open `http://localhost:3000`. API docs are at `http://localhost:8000/docs`.

Set `BRAVE_SEARCH_API_KEY` for live discovery. Without it, jobs fail visibly and no companies are fabricated. Gmail OAuth is implemented; configure its three variables before connecting. Mock sending remains explicit for development. Controlled autopilot, recipient verification, approved drafts, unpaused sending, and explicit bulk confirmation are required.

## Autonomous workflow

1. Choose **RESEARCH** or **DRAFT** under Agent control.
2. Open **Discovery**, create a campaign, and press **Start**.
3. The database-backed worker discovers company sites and researches relevant public business emails.
4. In DRAFT mode, open **Bulk review** to inspect evidence, approve selections, and preview exclusions.
5. Connect Gmail, switch to CONTROLLED AUTOPILOT, resume sending, and explicitly confirm the eligible batch.

## Verify

```text
cd backend && pytest
cd frontend && npm run typecheck && npm run lint && npm run build
```

See [setup](docs/SETUP.md), [architecture](docs/ARCHITECTURE.md), and [security](docs/SECURITY.md).
