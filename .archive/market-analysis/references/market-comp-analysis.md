# Live Market / Compensation Analysis

Method for running a real, data-backed market analysis of roles, skills, or industries — e.g. "what should I pay for role X", "is my skill in demand", or a career-market read. Built from the 2026 workflow: tinyfish search + fetch to triangulate live comp and demand signals, then synthesize into actionable bands.

## Two endpoints (see the `tinyfish` skill for full auth/usage)
- Search: `GET https://api.search.tinyfish.ai?query=<url-encoded>` (returns position, site_name, title, snippet, url, date)
- Fetch/scrape: `POST https://api.fetch.tinyfish.ai` with JSON `{"urls":[...],"format":"markdown"}`

## Workflow
1. **Define the unit before searching.** Name role(s), level band, geography/remote-vs-on-site, and what "market" means. Decide the output: a comp band to offer, negotiate-from, or pitch your own raise. This sets depth.
2. **Pull comp from ≥3 independent sources** in one batch of searches: Levels.fyi (staff/senior, big-tech), Glassdoor/Naukri/Indeed aggregators, and offer-showing communities. Run several queries per source (base vs total comp, junior vs senior).
3. **Pull demand signals** in parallel: posting volume (LinkedIn/Indeed job boards), "is X still hiring 2026" trend queries, and talent-shortage framing. Note rising vs falling.
4. **Pull live hiring activity**: company-specific + role queries (e.g. "Zscaler jobs Bengaluru", "<role> remote hiring India"). The company name + posting count is the strongest leading indicator of real demand.

## Triangulation rules (the core method)
- **Ranges beat point estimates.** Report min/median/top-band, not a single number. Averages from 1–2 datapoints are directional only — flag them as thin and never treat a single-datapoint figure as gospel.
- **Never trust one source.** Each has bias: Levels.fyi skews high/big-tech, offer communities post outliers (both directions), posted salaries often lie. Cross-check and state each source's bias in the output.
- **Comp ≠ demand.** A role can pay well but be shrinking (e.g. generic QA automation in 2026) or vice-versa. Report both axes separately, then synthesize where they intersect for the target user/profile.

## Synthesis output
- A **comp band** (min/median/top) per target role, with a confidence level and the bias caveat for each input.
- A **sensitivity table**: how the band moves when level/geo/company-size change.
- Key caveats on each data source's bias, so nobody treats one number as gospel.
- An **actionable recommendation** grounded in where comp AND demand actually intersect for the specific profile (not a generic list).

## Anti-patterns to avoid
- Do NOT present single-datapoint figures as authoritative. Flag them explicitly ("based on 1 salary").
- Do NOT flatten a role into one title — "engineer" varies wildly by company; keep level bands explicit.
- Do NOT skip demand signals — comp alone is a trap in a shrinking market.
