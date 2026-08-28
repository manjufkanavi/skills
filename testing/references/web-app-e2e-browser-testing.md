# Web Application E2E Browser Testing (Local Mock-Server Mode)

Browser-driven end-to-end testing of a web app (Next.js / React) against the
**real application code**, when production services (Postgres / MinIO /
Keycloak / Ollama / n8n) are unavailable and Docker is down.

Derived from testing the resume-platform: full journey in the browser —
landing → demo → dashboard → upload → **Re-run** → detail showing real ATS score
+ AI-written sections + suggestions.

## When to use

- User wants to verify a web app's UI flows end-to-end in the browser, not just
  unit/route tests.
- The production stack can't stand up (no Docker / no external services).
- You must exercise the **real app logic** (real routes, real OCR, real ATS
  engine, real LLM-improvement code with fallback) — only storage and auth are
  lightened.

## 1. Local mock-server mode

The goal is real app code with lightweight substitutes for external services:

| Production service | Local substitute |
|--------------------|------------------|
| Postgres | in-memory SQLite (aiosqlite) via guarded column-type shims |
| MinIO | in-memory byte store (upload / download / delete) |
| Keycloak / auth | stubbed: any non-empty `Bearer <token>` → fixed local user |
| Ollama | point at localhost so it fails fast → deterministic LLM fallback |

Enable local mode via an env flag (e.g. `LOCAL_DEV=1`). The production code path
is byte-for-byte unchanged when the flag is unset.

Bootstrap steps:
1. Start the backend mock-server (real FastAPI app, all routes) on `127.0.0.1:3006`.
2. Start the frontend dev server on `127.0.0.1:3007`, which proxies `/api/*` → `3006`.
3. Verify the proxy: `curl http://127.0.0.1:3007/api/v1/internal/health`.

## 2. Browser E2E workflow

1. Launch backend + frontend (both as tracked background processes).
2. Confirm both serve `/health`.
3. Drive the UI in the browser: landing → demo → dashboard → detail.
4. For the **critical backend-integration flow** (e.g. review → suggestion →
   remedy): upload a real file → click **Re-run** → confirm the detail page
   shows a real score + real AI-generated improvements.
5. Capture a screenshot as evidence of the rendered result.

## 3. Next.js 16 async Client Component gotcha

**Symptom:** A page renders once (from server HTML) but then shows an **empty
page** / suspends indefinitely on HMR or navigation. Dev log shows:
`<XPage> is an async Client Component. Only Server Components can be async.`
`A component was suspended by an uncached promise.`

**Root cause:** `"use client"` + `export default async function Page({ params })
{ const { id } = await params; }` — Next.js 16 does not support awaiting `params`
inside a client component.

**Fix:** Make the page a *synchronous* client wrapper that reads the route param
via `useParams()`, then delegates to a client child that holds all hooks:

```tsx
import { useParams } from "next/navigation";

export default function Page() {
  const rawId = useParams().id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId ?? "";
  return <DetailClient id={id} />;   // DetailClient is the hooks-bearing client component
}
```

If a clean restart after the edit still suspends, wipe `.next` and restart the
dev server (Turbopack can hold a stale build).

## 4. Injecting a real file into a React file-input (browser automation)

React-controlled `<input type="file">` cannot be populated by clicking the
(hidden) input, and `DataTransfer.add()` is **not supported in all browsers**
(WebKit/Playwright): `TypeError: dt.add is not a function`.

Two working approaches:

**A. `DataTransfer([file])` constructor** (when supported):
```js
const dt = new DataTransfer([file]);
input.files = dt.files;
input.dispatchEvent(new Event('change', { bubbles: true }));
```

**B. Minimal `FileList` mock** (works everywhere) — define `files` as a getter
returning an object with `length`, index access, and `item()`:
```js
const dt = new DataTransfer();
Object.defineProperty(input, 'files', {
  configurable: true,
  get: () => ({ length: 1, 0: file, item: (i) => (i === 0 ? file : null) }),
});
input.dispatchEvent(new Event('change', { bubbles: true }));
```

For React-controlled **text** inputs, set value via the native setter and emit
`input` + `change`:
```js
const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
setter.call(input, "Senior Software Engineer");
input.dispatchEvent(new Event('input', { bubbles: true }));
input.dispatchEvent(new Event('change', { bubbles: true }));
```

**localStorage access denied** on some pages (e.g. a suspended detail page):
re-set the token from a clean same-origin page (landing), then navigate to the
target page so it fetches with the token.

## 5. Debugging path — inspect the DB directly

**When the API GET hides internal state** (e.g. `minio_key` is not exposed in the
response, but the frontend can't work without it), the DB is the source of truth.

```bash
# Inspect schema:
python -c "import sqlite3; con=sqlite3.connect('local_resume.db');
print([c[1] for c in con.execute('PRAGMA table_info(resumes)').fetchall()])"

# Read the actual stored columns:
python -c "import sqlite3; con=sqlite3.connect('local_resume.db');
[print(r) for r in con.execute('SELECT id,filename,status,minio_key FROM resumes ORDER BY rowid DESC LIMIT 6')]"
```

Use this to confirm whether an upload actually persisted its file reference, or
whether a record is stuck with an internal key left empty.

## 6. Local-dev caveats

- **In-MinIO store is per-process.** A resume created by one API process cannot
  be re-run by another after restart — its `minio_key` points to an in-memory
  object that's gone. **Keep a single API process running** for consistent state.
- Scanned PDFs / images OCR to `""` when tesseract/Surya aren't installed; the
  LLM layer falls back to `_get_fallback_improvements` (real rewrite logic, no
  live model). Scores are realistic but not "live model" scores.
- Credentials/API keys present in a session must be redacted, not preserved.

## See also (in this skill)

- `references/fastapi-e2e-testing-patterns.md` — TestClient-based E2E (auth
  middleware ordering 401-before-422, file upload, bug docs in tests).
- `references/fastapi-deterministic-core-testing.md` — deterministic core + route
  smoke test without live Postgres/MinIO/Keycloak/Ollama.
- `references/tesseract-ocr-e2e-testing.md` — real OCR pipeline test.
