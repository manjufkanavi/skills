---
name: playwright-e2e
description: "Automated Playwright E2E suite testing a web app live."
version: 1.0.0
author: Hermes Agent (autonomous curation)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [qa, testing, browser, web, playwright, e2e]
    related_skills: [dogfood, testing]
---

# Playwright E2E Browser Testing (Live Dev-Server Mode)

Programmatic, automated end-to-end testing of a web app (Next.js / React / Vue)
against the **real application code** running on a local dev server, when production
services (Postgres / MinIO / Keycloak) are unavailable and Docker is down.

This is **automated suite authoring** (deterministic specs, assertions, CI-runnable),
not exploratory QA. For browser-tool-driven *exploratory* bug-hunting, use `dogfood`.

## When to use

- User wants UI flows verified end-to-end in an automated suite, not just unit/route tests.
- The production stack can't stand up (no Docker / no external services).
- You must exercise the **real app logic**; storage/auth are lightened or absent.

## Bootstrap before writing any test

```bash
npx playwright install chromium          # ~94 MiB, one-time per machine
# Start the frontend dev server (e.g. next dev -p 3007) as a background process
# Confirm it serves HTTP 200 on / before driving the UI:
curl -s -o /dev/null -w "%{http_code}" http://localhost:3007/   # expect 200
```

A server returning `200` is ready; poll until it does. Never assert on a page that
hasn't finished rendering — wait for the URL or content first.

## Deterministic matchers (the non-obvious ones)

These are the lessons that cost real debugging time and generalize to any web app:

### 1. Backend unreachable means NO response — don't use `waitForResponse`
When the API is unreachable, calls throw (`Failed to fetch`) and **never return a
response**. `page.waitForResponse` will hang until the 30s test timeout. Instead,
capture requests as they fire and poll:

```ts
const uploadRequests = [];
page.on("request", (req) => {
  if (req.url().includes("/api/v1/resume/upload") && req.method() === "POST") {
    uploadRequests.push(req);
  }
});
await analyzeBtn.click();
// Poll for the request to fire (proves the live path), then assert on surfaced error.
await expect.poll(() => uploadRequests.length, { timeout: 10_000 }).toBeGreaterThan(0);
await expect(page.locator("p.text-rose-400").first()).toBeVisible();
```

### 2. Native `<button>` uses the real `disabled` attribute — assert with matchers
Custom button components render a native `<button>`. When disabled it carries the real
`disabled` attribute (not `aria-disabled`). Use Playwright's matchers:

```ts
await expect(analyzeBtn).toBeDisabled();   // disabled until a file is set on the input
await expect(analyzeBtn).toBeEnabled();    // enabled after a file is set
```
Do NOT assert `toHaveAttribute("disabled")` or check `aria-disabled`.

### 3. Hidden file inputs — set files directly
React-controlled `<input type="file">` is hidden; clicking it in Playwright is unreliable.
Set files directly on the input with a valid `mimeType` (PDF, DOCX, JPG, PNG):

```ts
const input = page.locator("input[type=\"file\"]").first();
await input.setInputFiles({ name: "sample.pdf", mimeType: "application/pdf" });
```

### 4. Component renders as a `<div>`, not an h-tag → match by text
UI primitives like Radix `CardTitle` render `<div>` elements, not h1–h6.
`getByRole("heading")` cannot find them — match by text:

```ts
await expect(page.getByText("Profile extracted")).toBeVisible();   // not getByRole heading
```

### 5. Ambiguous matchers cause strict-mode violations
Two buttons with the same meaning but different labels ("Try Demo" vs "Try the demo")
matched by `/try demo/i` triggers a strict-mode locator violation. Target exact labels:

```ts
await page.getByRole("button", { name: "Try the demo" }).click();   // exact, not regex
```

### 6. Wait for client-side routing before asserting page content
After clicking a card's "Review" `<Link>`, wait for the URL before asserting content:

```ts
await page.getByRole("link", { name: /review/i }).first().click();
await expect(page).toHaveURL(/\/resume\//);   // wait for client-side nav first
await expect(page.getByText("Profile extracted")).toBeVisible();
```

### 7. Error messages are plain `<p>` tags with no role/label
Errors render as `<p className="text-rose-400">…</p>` — no role, no label. Match by
class + text:

```ts
await expect(page.locator("p.text-rose-400").first()).toBeVisible();
```

## Fixture files for uploads

No sample file ships with the repo. Create a minimal valid one and store it at
`tests/fixtures/sample.pdf`. The file bytes are irrelevant — Playwright just needs a
valid `File` object; the app only checks name + mimeType.

## See also (in this skill)

- `references/playwright-e2e-patterns.md` — worked example from the resume-platform
  WebUI: landing → login/signup → demo mode (dashboard/upload/logout) → resume detail
  with re-run/delete. Includes the passing spec set and fixture guidance.
