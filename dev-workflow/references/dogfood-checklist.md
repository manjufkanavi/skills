# Dogfood / QA Checklist (from original dogfood skill)

## 5-phase systematic workflow

1. **Plan** — Create output dirs, identify scope, build rough sitemap
2. **Explore** — Navigate, snapshot, check console errors, click interactives
3. **Collect** — Screenshots, details, classify issues (severity + category)
4. **Categorize** — Deduplicate, assign severity (Critical/High/Medium/Low)
5. **Report** — Executive summary, per-issue sections, summary table

## Key tips
- Always check `browser_console()` after navigating and after significant interactions
- Use `annotate=true` with `browser_vision` for element positioning
- Test with both valid and invalid inputs
- Scroll through long pages — content below fold may have issues
- Test edge cases: empty states, very long text, special characters
