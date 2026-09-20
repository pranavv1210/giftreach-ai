# Discovery providers

## OpenStreetMap Overpass

This is the default no-key provider. It queries named campaign areas for mapped offices and companies that include an official website, then passes those websites to the existing contact-research stage. Public Overpass servers are community infrastructure: campaigns are intentionally bounded and sequential, results are cached in the application database, and coverage may be incomplete. For commercial scale, use a hosted or self-hosted Overpass instance.

No API key is required. Configure `OVERPASS_API_URL` only if using a different permitted instance.

## Brave Search

The implemented live company provider generates bounded queries from campaign locations and industries and calls the official Brave Search API. Candidate URLs are normalized by domain and common social/directory results are excluded. Every candidate retains its query, result URL, and snippet. A snippet is evidence of discovery only, not proof of gifting activity or business facts.

Set `BRAVE_SEARCH_API_KEY` in `backend/.env`. Brave controls current quotas and pricing. Missing credentials produce a visible failed/retrying job; the application never inserts fake fallback companies.

## Official company websites

The contact provider visits the candidate homepage plus `/contact`, `/about`, `/team`, and `/careers`. It accepts only same-domain email addresses whose nearby public text or mailbox name is relevant to HR, People, engagement, administration, procurement, workplace, talent, or culture. It does not log in, solve CAPTCHAs, scrape LinkedIn, or infer email patterns. Results remain `SYNTAX_VALID` and are not send-eligible until independently or manually verified.

## Test provider

Tests inject deterministic provider adapters. Those records exist only in disposable test databases and are never offered as live discovery results.
