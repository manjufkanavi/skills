# Architecture Review Pattern

## Core method (from original architecture-review skill)

1. **Understand the project** — README, architecture docs, code, tests, deployment
2. **Service inventory audit** — classify every dependency:
   - ✅ Solves real user need
   - ⚠️ Nice to have / can defer 3 months
   - ❌ Unnecessary
3. **"One thing" test** — find the project's real moat
4. **Alignment review** — code vs docs, build vs run, phase breakdown
5. **Deliver verdict** — ✅ Good, ⚠️ Tighten, 🎯 Real moat, 📋 Next steps

## Shared Pitfalls

- Don't just list problems — pair with recommendations (defer, simplify, keep)
- Don't assume minimalism is always right — informed over-engineering is fine
- Distinguish "I would do differently" from "actively harmful"
- Don't ignore working code — scope review is about future decisions, not past judgment
