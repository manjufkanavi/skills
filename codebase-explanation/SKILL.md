---
name: codebase-explanation
description: Explain how an existing project works end-to-end.
created: 2026-09-19
updated: 2026-09-19
---

# Codebase Comprehension Walkthrough (Methodology + Worked Example)

**Load when:** "explain how this works", "read and understand the repo, explain everything with a flow diagram", "walk me through the architecture".

This is an *explanation/onboarding* task, distinct from `Architecture Review` (dev-workflow module 1), which *assesses quality* before committing to work. Goal here: produce an accurate, teachable walkthrough with flow diagrams — not a verdict.

## Methodology (7 steps)

1. **Map the shell first.** Top-level files, git remote + branch, and a depth-3 tree (exclude `.git`, `node_modules`, `.venv`). Spot the stack from `package.json` / `requirements.txt` / `Dockerfile` / docker-compose.
2. **Read the design doc if present.** It is often THE source of truth for *intended* design — but treat it as a hypothesis, not fact. You will find the real gaps in step 6.
3. **Read entry points.** App main (FastAPI `app = ...`, Next.js `layout.tsx`), router registration / middleware, startup & shutdown hooks.
4. **Trace services in dependency order:** auth → routes/services (core logic) → storage/external integrations. Read the service that *does* work before the one that just calls it.
5. **Map deployment + routing.** nginx vhosts (which path → which port, auth-wrapper vs direct), docker-compose services + exposed ports + healthchecks, Cloudflare tunnel rules.
6. **Build the diagrams.** Cover four things: (a) end-to-end request lifecycle, (b) the core processing pipeline, (c) auth flow, (d) data model. ASCII is fine and renders on Telegram/CLI.
7. **Surface doc-vs-code gaps.** This is where real understanding lives — the difference between what docs claim and what code actually does.

## Patterns worth hunting for (they show up in most real platforms)

- **Dual / alternative execution paths.** A synchronous inline path (e.g. API endpoint runs everything) AND an async engine pipeline (n8n, Celery, workers). Trace BOTH — a walkthrough that misses the second is incomplete.
- **Preview / demo fallbacks.** Frontend falls back to fixture/demo data when the backend is unreachable, so every page renders for previews/screenshots without a live server. Look in data hooks / API clients (`try real → catch demo`).
- **Auth fallback chains.** Try a proxy/wrapper first, fall back to direct provider introspection. (`validate_token` → wrapper `/validate`, then Keycloak introspection).
- **Internal vs external API split.** Internal endpoints (called by other services, not users) use a shared-secret header instead of JWT. Nginx routes `/internal/` straight to the app, bypassing auth-wrapper; user paths go through it.
- **Deterministic-vs-LLM split.** Scoring is a pure function (no LLM); improvement generation calls the model with a JSON-extraction + fallback-on-failure pattern.

### Other knowledge banks (references/)
- **iacgenie-platform** (`references/iacgenie-platform.md`): two-product monorepo — IaCGenie (FastAPI + Celery agentic pipeline → OpenTofu/Docker/K8s via Gemini, multi-model registry) and LightSerp (TypeScript SERP/scrape MCP). Shared Docker stack, Cloudflare+nginx access layer. Key gotcha: backend README lags reality (SQLite default vs real PostgreSQL/Alembic; Gemini-only text vs multi-model registry).

## Worked example — resume.platform (condensed knowledge bank)

Full detail: repo `resume-platform/`, file `ARCHITECTURE.md` (1034 lines). Domain: AI resume review at `resume.iacgenie.com`.

**Stack / ports (reuses the shared IacGenie Docker stack on 192.168.0.118):**
- Next.js 15 SPA (App Router, Tailwind + shadcn/ui) — served by the API container.
- FastAPI (`api/`) on `127.0.0.1:3006` — REST API + orchestrator.
- n8n (`iacgenie_n8n`) on `127.0.0.1:3005` — async pipeline engine, queue mode on Redis.
- Ollama `qwen2.5:0.5b` on host `11434` — local LLM for improvements (~2–5s/response, CPU).
- Shared: Postgres (JSONB results), Redis (n8n queue), MinIO (`resume-files` bucket for PDF/DOCX/JPG bytes), Keycloak OIDC via auth-wrapper (`:9096`).

**Two processing paths (the key structural insight):**
- **Inline path:** `POST /api/v1/resume/{id}/regenerate` runs OCR → ATS score → LLM improvements in one request. This is what the UI's "Re-run" button calls.
- **Async path:** API → n8n webhook (`resume-pipeline.json`: Webhook → OCR node → ATS code node → LLM improvements → save-results) runs the same pipeline queued. n8n calls back into internal endpoints (`POST /api/v1/internal/n8n/ocr`, `/process-resume`) guarded by a shared `API_SECRET` header.

**Core services (`api/services/`):**
- `ocr.py` — 3-layer fallback: pypdf (PDF text) → tesseract (scanned images) → Surya (image OCR). `parse_text_to_json()` buckets raw text into sections by header keywords (contact_info/summary/experience/education/skills).
- `ats.py` — **deterministic** scoring, 4 weighted factors: Completeness 30% (required sections present), Formatting 25% (bullets/spacing/word-count 100–1000), Keyword Match 30% (detects industry from job_title → keyword pool: software/data/devops/design/marketing/finance), Section Quality 15% (action verbs + quantified achievements).
- `llm.py` — builds a prompt from OCR JSON + ATS score, POSTs to Ollama (temp 0.3), parses the returned JSON; if Ollama is down, returns deterministic fallback suggestions from the ATS recommendations.
- `minio.py` — upload/download/delete by object key; `auth.py` — JWT validation via auth-wrapper then Keycloak introspection fallback.

**Data model:** `users` (id, keycloak_id unique, email unique) ↔ `resumes` (JSONB columns: ocr_json, ats_score_json, improvements_json; status pending/processing/completed/failed). File bytes live in MinIO under `resumes/{uuid}_{filename}`; all analysis is JSONB so scoring evolves without schema migrations. Duplicate guard = (user_id, filename) checked before MinIO write + IntegrityError→409.

**Auth flow:** `/login` → redirect to Keycloak (`response_type=code`) → `?code=` on `/auth/callback` → exchange for token (preview completes a demo session) → store `{token,user}` in localStorage → API calls send `Authorization: Bearer <jwt>`; nginx routes `/api/v1/` through auth-wrapper, `/api/v1/internal/` straight to the API.

**Preview-fallback pattern (reusable):** `webui/src/lib/use-data.ts` hooks call the real API, then on failure swap in demo fixtures (`demo.ts`) so every page renders for previews/screenshots with no live backend. `auth-context` has a matching `loginDemo()`.
