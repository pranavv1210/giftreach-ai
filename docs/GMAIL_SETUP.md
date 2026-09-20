# Gmail setup

Create a Google Cloud project, enable Gmail API, configure an OAuth consent screen, and create a Web OAuth client. Configure `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, and `GMAIL_REDIRECT_URI` as server-side secrets. Use the narrow `gmail.send` scope for sending; add `gmail.modify` only if reply/thread synchronization is enabled. Google may require consent verification for external production users.

The backend implements authorization, callback state validation, encrypted token storage, token refresh, Gmail API send, connection status, and revocation. Add the exact configured callback URL to the Google OAuth client. After restarting, use **Integrations → Connect**.

Bulk Gmail sends require verified recipients, approved valid drafts, CONTROLLED_AUTOPILOT, resumed sending, all global/company limits, and explicit confirmation. Automated tests never call Google. Reply and bounce synchronization are not implemented yet.
