# Testing

Backend tests exercise authentication, campaign creation, unavailable providers, autonomous discovery with mock adapters, company deduplication, multiple contacts, provenance, batch drafts, policy validation, bulk approval, unverified exclusion, cancellation, suppression, idempotency, missing Gmail safety, and emergency stop. They never send real mail. Run `pytest` in `backend`. Frontend verification uses strict TypeScript, ESLint, and a production Next.js build.
