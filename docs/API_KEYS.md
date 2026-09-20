# API keys

All integrations are optional for local UI and mock-send development.

- `BRAVE_SEARCH_API_KEY`: required for live company discovery. Obtain it from Brave Search API. Plans, quotas, and free allowances can change, so review current pricing before enabling it.
- `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REDIRECT_URI`: required for Gmail OAuth sending.
- `TOKEN_ENCRYPTION_KEY`: recommended separate random secret for encrypting stored Gmail tokens; otherwise `APP_SECRET` is used.
- `EMAIL_VERIFICATION_API_KEY`: reserved for a verification provider. No third-party verification provider is implemented yet; public results remain SYNTAX_VALID until manually or independently verified.
- `OPENAI_API_KEY`: optional/future. Validated rule templates work without AI.
- `DATABASE_URL`: selects SQLite or PostgreSQL.

Never put secrets in frontend variables or commit `.env`.
