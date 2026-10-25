---
name: async-pipeline-route-testing
description: Integration-test async FastAPI pipeline routes offline.
tags: [testing, integration-test, fastapi, asyncio, monkeypatch, pipeline-route]
related_skills: [testing, debugging]
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Async Pipeline Route Integration Testing

Integration-testing an **async route that runs a multi-stage inline pipeline**
against the real FastAPI app, with external services replaced by fakes.

## When to use this

- Target is an `async def` route that spawns threads / awaits coroutines inside
  a pipeline (e.g. `/resume/<id>/regenerate`), not just a stateless endpoint.
- External services (MinIO, Ollama, Keycloak) are offline and must be replaced
  by fakes — but you still want to exercise the real route, middleware stack,
  and DB persistence path.
- The route opens its own connection via `get_db` (dependency not injected).

## Core technique

1. **Patch module-level names on the routes module**, not local import aliases:
   `monkeypatch.setattr(routes.resumes, "get_db", fake_get_db)`. The route looks
   up names on its own module at call time.
2. **Stub `download_file` to return bytes** and patch `extract_text_from_file`
   (not the OCR layer) to return parsed plain text — do NOT decode binary DOCX/
   PDF bytes as UTF-8. Keep `file_type` consistent with the real pipeline.
3. **Fake `get_db` as an `asynccontextmanager` that yields a shared instance** —
   see the three-bug pitfalls below; the state-loss bug is the most common.

## The three bugs that break these tests (quick reference)

Full walkthroughs, code, and fixes are in
`references/async-pipeline-route-testing.md`:

| # | Symptom | Root cause / fix |
|---|---------|------------------|
| 1 | `object dict can't be used in 'await'` | Fake `_run_stage` is a sync `def` returning `fn()`; route awaits that dict. Make the fake an `async def` and call `fn()` without awaiting (route awaits the coroutine's result). |
| 2 | Assertion state lost (`db.commits` stays 0) | `asynccontextmanager` yields a **new** FakeDB each call; captured reference isn't the one used. Share per-test state via a `holder` dict read from both sides of the patch. |
| 3 | "Stream has ended unexpectedly" (500 or empty) | Route does `return <async helper>` instead of `await`. Starlette serializes the coroutine. Await every async helper at its call site; also await `db.commit()` (real session commit is async). |

## LSP false positives to ignore here

- `NoReturn` used only as a return annotation triggers "unused import" from
  pyright — it IS needed. Keep the import; trust test behavior over the linter.
- After rewriting a function, `Future` / `ThreadPoolExecutor` imports often
  become genuinely dead — remove those (unlike the `NoReturn` case).

## Verification discipline (no regressions)

1. Run the full suite **before** changes to record the baseline count
   (`grep -E "passed|failed" | tail`). A pass that does nothing is a missed
   learning opportunity.
2. After changes, run the full suite again — assert `passed` increased by your
   new count and nothing dropped. Warnings are fine; failures/imports errors
   are not.
3. When a test passes but an unexpected `ERROR` log appears, read its source —
   a passing assertion can still mask a subtly-wrong fake (e.g. OCR raising
   before your `fake_run_stage` ever runs).

See Also: overlaps with the user-owned `testing` skill — this one is focused on
the async-pipeline-route sub-class (monkeypatched deps + fake DB).
