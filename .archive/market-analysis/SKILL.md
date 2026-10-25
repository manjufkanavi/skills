---
name: market-analysis
description: Live role pay and demand analysis. Use for any value query.
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [market-research, compensation, hiring, demand-analysis]
related_skills: [deep-research, competitor-news-monitor, tinyfish]
---

# Market Analysis

Run a real, data-backed market analysis of roles, skills, or industries. Produces compensation bands and demand signals triangulated from live sources, then synthesizes actionable ranges with explicit confidence levels — not generic advice.

Built for the 2026 workflow: Tiny Fish search + fetch to pull live comp and demand, then synthesize into bands grounded in where comp AND demand actually intersect for the specific profile.

## When to use
- "What should I pay for role X?" / "market rate" / "is this salary fair"
- "Is [skill/role] in demand?" or "career market analysis for X"
- Negotiation prep — need a comp band to offer from or pitch against
- A user shares their CV/resume and asks "what's my market value"

## Prerequisites
1. **Define the unit before searching.** Name role(s), level band (junior/mid/senior/staff — comp varies wildly within one title), geography/remote-vs-on-site, and what "market" means (all-tech vs a slice like fintech or security startups). Decide the output: offer band, negotiate-from point, or self-pitch. This sets depth.
2. Load the `tinyfish` skill for API auth + endpoints (search: GET, fetch/scrape: POST).

## Workflow
1. **Pull comp from ≥3 independent sources** in one batch of searches: Levels.fyi (staff/senior, big-tech), Glassdoor/Naukri/Indeed aggregators, and offer-showing communities. Run several queries per source (base vs total comp; junior vs senior).
2. **Pull demand signals** in parallel: posting volume (LinkedIn/Indeed job boards), "is X still hiring 2026" trend queries, talent-shortage framing. Note rising vs falling separately.
3. **Pull live hiring activity**: company-specific + role queries (e.g. "Zscaler jobs Bengaluru", "<role> remote hiring India"). The company name + posting count is the strongest leading indicator of real demand — often more telling than comp.

See `references/market-comp-analysis.md` for the full method, triangulation rules, and anti-patterns.

## Output
- A **comp band** (min / median / top) per target role, with a confidence level and each source's bias caveat.
- A **sensitivity table**: how the band moves when level / geography / company-size change.
- Key caveats on each data source's bias, so nobody treats one number as gospel.
- An **actionable recommendation** grounded in where comp AND demand actually intersect for the specific profile — not a generic list.

## Anti-patterns
- Do NOT present single-datapoint figures as authoritative — flag thin samples ("based on 1 salary") and treat them as directional only.
- Do NOT flatten a role into one title — "engineer" varies by company; keep level bands explicit.
- Do NOT skip demand signals — comp alone is a trap in a shrinking market (e.g. generic QA automation, 2026).

## Related
- `references/market-comp-analysis.md` — full method, endpoints, triangulation rules.
- `tinyfish` — the search/fetch API used to pull live data.
- `deep-research` — heavier multi-source research runs (report + slideshow).
