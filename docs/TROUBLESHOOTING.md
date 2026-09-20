# Troubleshooting

- “Session expired”: sign in again and confirm browser cookies are allowed.
- CORS error: set `FRONTEND_ORIGIN` to the exact dashboard origin.
- Send rejected: confirm the draft is approved, recipient is manually/provider/MX verified, mode is CONTROLLED AUTOPILOT, sending is resumed, and no suppression or kill switch is active.
- Gmail “missing configuration”: expected until OAuth client variables are configured; mock development remains available.
- Campaign shows “Provider error”: open Activity logs and confirm `BRAVE_SEARCH_API_KEY` is present in `backend/.env`, then restart the backend and start the campaign again.
- Campaign stays queued: choose RESEARCH or DRAFT mode, clear global/discovery pause, and keep the backend running because it hosts the worker.
