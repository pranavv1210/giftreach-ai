# Security

Secure defaults include HTTP-only SameSite cookies, signed 12-hour sessions, CSRF tokens on mutations, exact-origin CORS, server-only secrets, authorization on all business endpoints, suppression and kill-switch checks at the send boundary, and no logging of message bodies or credentials. Set `environment=production` to require Secure cookies behind HTTPS.

Before production, add a managed secret store, at-rest encryption for OAuth tokens, reverse-proxy rate limiting for login, CSP/security headers, PostgreSQL backups, dependency scanning, and central audit-log retention. Never expose the API directly without TLS.

