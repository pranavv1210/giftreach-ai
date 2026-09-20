# Gmail setup

Create a Google Cloud project, enable Gmail API, configure an OAuth consent screen, and create a Web OAuth client. Configure `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, and `GMAIL_REDIRECT_URI` as server-side secrets. Use the narrow `gmail.send` scope for sending; add `gmail.modify` only if reply/thread synchronization is enabled. Google may require consent verification for external production users.

The current MVP deliberately does not perform real delivery: the Gmail status is configuration-aware, while sends use the labelled mock provider. A production Gmail provider still needs the OAuth callback, encrypted refresh-token storage, revocation, and message/thread synchronization before real sending can be enabled.

