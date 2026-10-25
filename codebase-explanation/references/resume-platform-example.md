# Worked Example — resume.platform

Full detail: repo `resume-platform/`, file `ARCHITECTURE.md` (1034 lines). Domain: AI resume review at `resume.iacgenie.com`. This is a condensed knowledge bank for the codebase-explanation skill.

## Stack / ports (reuses shared IacGenie Docker stack on 192.168.0.118)

- Next.js 15 SPA (App Router, Tailwind + shadcn/ui) — served by the API container.
- FastAPI (`api/`) on `127.0.0.1:3006` — REST API + orchestrator.
- n8n (`iacgenie_n8n`) on `127.0.0.1:3005` — async pipeline engine, queue mode on Redis.
- Ollama `qwen2.5:0.5b` on host `11434` — local LLM for improvements (~2–5s/response, CPU).
- Shared: Postgres (JSONB results), Redis (n8n queue), MinIO (`resume-files` bucket for PDF/DOCX/JPG bytes), Keycloak OIDC via auth-wrapper (`:9096`).

## Two processing paths (the key structural insight)

- **Inline path:** `POST /api/v1/resume/{id}/regenerate` runs OCR → ATS score → LLM improvements in one request. This is what the UI's "Re-run" button calls.
- **Async path:** API → n8n webhook (`resume-pipeline.json`: Webhook → OCR node → ATS code node → LLM improvements → save-results) runs the same pipeline queued. n8n calls back into internal endpoints (`POST /api/v1/internal/n8n/ocr`, `/process-resume`) guarded by a shared `API_SECRET` header.

## Core services (`api/services/`)

- `ocr.py` — 3-layer fallback: pypdf (PDF text) → tesseract (scanned images) → Surya (image OCR). `parse_text_to_json()` buckets raw text into sections by header keywords (contact_info/summary/experience/education/skills).
- `ats.py` — **deterministic** scoring, 4 weighted factors: Completeness 30% (required sections present), Formatting 25% (bullets/spacing/word-count 100–1000), Keyword Match 30% (detects industry from job_title → keyword pool: software/data/devops/design/marketing/finance), Section Quality 15% (action verbs + quantified achievements).
- `llm.py` — builds a prompt from OCR JSON + ATS score, POSTs to Ollama (temp 0.3), parses returned JSON; if Ollama is down, returns deterministic fallback suggestions from the ATS recommendations.
- `minio.py` — upload/download/delete by object key; `auth.py` — JWT validation via auth-wrapper then Keycloak introspection fallback.

## Data model

`users` (id, keycloak_id unique, email unique) ↔ `resumes` (JSONB columns: ocr_json, ats_score_json, improvements_json; status pending/processing/completed/failed). File bytes live in MinIO under `resumes/{uuid}_{filename}`; all analysis is JSONB so scoring evolves without schema migrations. Duplicate guard = (user_id, filename) checked before MinIO write + IntegrityError→409.

## Auth flow

`/login` → redirect to Keycloak (`response_type=code`) → `?code=` on `/auth/callback` → exchange for token (preview completes a demo session) → store `{token,user}` in localStorage → API calls send `Authorization: Bearer <jwt>`; nginx routes `/api/v1/` through auth-wrapper, `/api/v1/internal/` straight to the API.

## Preview-fallback pattern (reusable)

`webui/src/lib/use-data.ts` hooks call the real API, then on failure swap in demo fixtures (`demo.ts`) so every page renders for previews/screenshots with no live backend. `auth-context` has a matching `loginDemo()`.
