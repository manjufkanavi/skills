# Integration-testing an async multi-stage pipeline route offline

Walkthrough of the three bugs that break these tests and how each was fixed,
captured while testing resume-platform's inline `/resume/<id>/regenerate` route.

## Bug 1 — `object dict can't be used in 'await'`

The route does:
```python
ocr_json = await _run_stage(extract, "OCR stage")
ats_score  = await _run_stage(calculate_ats_score, "ATS scoring")
improvements = await _run_stage(generate_improvements, "LLM improvements")
```

If the fake `_run_stage` is a **sync** `def` that returns `fn()`, then the
route's outer `await` tries to await a plain **dict** → crash.

Fix: make the fake an `async def` and call `fn()` WITHOUT awaiting it (the route
awaits the coroutine's result, which is already resolved):
```python
async def fake_run_stage(fn, stage_name):
    if stage_name == "LLM improvements":
        raise routes.resumes.StageTimeout("Ollama timed out")
    return fn()   # OCR/ATS run inline here; route awaits this coroutine's result
```

Do NOT write `return await fn()` — `fn` is a plain lambda returning a dict, so
awaiting it fails. Only the outer `_run_stage` call is awaited by the route.

## Bug 2 — DB state lost across calls (fresh FakeDB each call)

The route does `async with get_db() as db:` **once**, but a monkeypatched
`get_db` that does `yield _FakeDB(resume)` creates a **new** instance each call.
Your test's captured reference is never the one actually used, so per-instance
counters (e.g. `db.commits`) stay 0 and the assertion fails even though the code
path executed.

Fix: share a **single per-test `holder` dict** between the patched function and
the assertions — never rely on a reference created inside an `asynccontextmanager`:
```python
def test_something(self, monkeypatch):
    holder = {}                       # shared by both sides of the patch
    resume = _make_resume()

    @asynccontextmanager
    async def fake_get_db():
        holder["db"] = _FakeDB(resume)   # store on the shared dict
        yield holder["db"]

    monkeypatch.setattr(routes.resumes, "get_db", fake_get_db)
    # ... hit the route via TestClient ...
    db = holder["db"]                   # read from the SAME dict, not a new instance
    assert db.commits >= 1
```

## Bug 3 — "Stream has ended unexpectedly" (500 or empty response)

If a route calls an `async def` helper and does `return _pipeline_failure(...)`
instead of `await`, Starlette tries to serialize the **coroutine** as JSON → the
response stream ends before any body is written.

Fix: `await` every async helper at its call site inside the route, and make
helpers that must persist DB state `await db.commit()` (the real session's
`commit` is async — an unawaited coroutine does not commit).

## Shared helper recipe (deterministic, no live services)

- Stub `download_file` to return the **DOCX bytes**; patch
  `extract_text_from_file` (not OCR) to return the **parsed plain text** — do
  NOT decode binary DOCX/PDF bytes as UTF-8 (it raises). Keep `file_type`
  consistent with what the real pipeline expects.
- Build `_make_docx_bytes()` so paragraphs parse into standard sections; add a
  sibling `_make_docx_text()` returning matching plain text so OCR→parse is faithful.
- Patch `get_db` on the **routes module** (`routes.resumes.get_db`), not a
  local import alias.

## Verification discipline (no regressions)

1. Run the full suite **before** changes to record baseline count:
   `grep -E "passed|failed" | tail`. A pass that does nothing is a missed learning opportunity.
2. After changes, run the full suite again — assert `passed` increased by your new count and nothing dropped.
3. When a test passes but an unexpected `ERROR` log appears, read its source — a passing assertion can still mask a subtly-wrong fake (e.g. OCR raising before your `fake_run_stage` ever runs).

## LSP false positives to ignore here

- `NoReturn` used only as a return annotation triggers "unused import" from pyright — it IS needed. Keep the import; trust test behavior over the linter.
- After rewriting a function, `Future` / `ThreadPoolExecutor` imports often become genuinely dead — remove those (unlike the `NoReturn` case).
