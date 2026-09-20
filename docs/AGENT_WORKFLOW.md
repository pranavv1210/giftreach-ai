# Agent workflow

Modes are OFF, RESEARCH, DRAFT, and CONTROLLED AUTOPILOT. RESEARCH runs discovery and contact research. DRAFT additionally queues draft generation. CONTROLLED AUTOPILOT permits delivery, but bulk approval and confirmation remain mandatory. The worker never bypasses recipient verification, suppression, pause state, kill switch, or global/company limits.

Create and start campaigns from **Discovery**. Their persistent jobs progress through DISCOVER → RESEARCH_COMPANY → GENERATE_DRAFT. Provider failures are recorded on both the job and campaign. Review results in **Bulk review**, where source evidence and exclusion reasons remain visible.
