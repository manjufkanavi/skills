# Playwright E2E Worked Example — Resume Platform WebUI

Worked example from the resume-platform Next.js SPA (branch `feat/phase0-auth-keycloak`,
WebUI dev server on port 3007). All flows exercise the **real app code**; when no
backend is reachable, pages fall back to demo fixtures and uploads surface local errors.

Passing suite: 12 tests across 3 specs, ~3s runtime against the live dev server.

## Spec set and what each verifies

### tests/e2e/landing.spec.ts (4)
- Landing page renders hero + CTA.
- Navbar "Try Demo" button exists and is clickable (sets a demo token; does NOT navigate).
- Upload page reachable via navbar.
- Login form renders Email/Password fields + "Try the demo" button; signup link present.
- Signup form renders Email/Password (exact label) + Confirm password fields; navigates back.

### tests/e2e/demo-flow.spec.ts (4)
- Login "Try the demo" navigates to `/dashboard` and shows a dashboard with 5 demo resumes.
- Hidden upload-first CTA is present on the empty-state-free dashboard view.
- Upload flow: set a file → POST fires to `/api/v1/resume/upload` (captured via request
  listener) → error message surfaces. **The button is disabled until a file is set.**
- Logout works (asserts the logout action triggers).

### tests/e2e/detail-flow.spec.ts (4)
- Card "Review" link navigates to `/resume/[id]` and shows profile + analysis sections.
- Back button returns to the dashboard.
- Delete flow: delete confirms and removes the card, returning to dashboard.
- Re-run is enabled on demo fixture `demo-1` (status completed, has both ats_score and
  improvements) — clicking fires a real `POST /resume/[id]/regenerate` that rejects locally.

## Key implementation notes from this session

### Deterministic auth entry point
Two buttons share a "Try Demo" meaning but have different labels:
- Navbar → **"Try Demo"** (sets token only, no navigation).
- Login form → **"Try the demo"** (persists token AND navigates to `/dashboard`).

Matching by `/try demo/i` triggers a strict-mode locator violation. Target the exact
label `"Try the demo"` on the login-form button — it's the only one that navigates.

### Card navigation waits for client-side routing
```ts
await page.getByRole("link", { name: /review/i }).first().click();
await expect(page).toHaveURL(/\/resume\//);   // wait for nav before asserting content
```

### "Profile extracted" is a CardTitle (a `<div>`, not an h-tag)
Match by text, not `getByRole("heading")`.

### Upload button disabled state + hidden file input
```ts
const analyzeBtn = page.getByRole("button", { name: /analyze resume/i });
await expect(analyzeBtn).toBeDisabled();   // disabled until a file is set on the input
const input = page.locator('input[type="file"]').first();
await input.setInputFiles({ name: "sample.pdf", mimeType: "application/pdf" });
```

### Backend-unreachable → no response; use a request listener + poll
`waitForResponse` hangs when the API is unreachable. Capture requests as they fire:
```ts
const uploadRequests = [];
page.on("request", (req) => {
  if (req.url().includes("/api/v1/resume/upload") && req.method() === "POST") {
    uploadRequests.push(req);
  }
});
await analyzeBtn.click();
await expect.poll(() => uploadRequests.length, { timeout: 10_000 }).toBeGreaterThan(0);
await expect(page.locator("p.text-rose-400").first()).toBeVisible();
```

### Error messages are plain `<p>` tags with no role/label
```ts
await expect(page.locator("p.text-rose-400").first()).toBeVisible();
```

## Fixture file for uploads

No sample PDF ships with the repo. Create a minimal valid one:
```bash
printf '%%PDF-1.4\nxref\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n95\n%%%%EOF' > tests/fixtures/sample.pdf
```

Store it at `tests/fixtures/sample.pdf`. The bytes are irrelevant — Playwright needs a
valid `File` object; the app only checks name + mimeType.

## Running the suite
```bash
# From webui/ — starts dev server, installs chromium if needed, runs the suite
npx playwright test --config=playwright.config.ts
```

## What was fixed to get green (debugging lessons)
- `Profile extracted` is a `<div>` → switched to text match.
- Delete/re-run tests raced client-side nav → added `waitForURL(/\/resume\//)`.
- Upload test hung 30s → switched from `waitForResponse` to a request listener + poll.
- Upload button never became clickable → set the hidden file input first.
