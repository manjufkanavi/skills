---
name: api-learning-course
description: Build hands-on API courses with runnable scripts.
version: 1.0
author: Tiel-Coder (Hermes Agent)
license: Apache-2.0
metadata.hermes.tags: [api, python, rest, tutorial, course]
metadata.hermes.related_skills: [tech_teacher, testing, github-repo-management]
---

Build a hands-on, learn-by-doing course around an API (REST APIs most often).

## When to Use
Build this when the user wants a hands-on course/tutorial/curriculum for an API — REST APIs, teach-by-doing Python lesson series with runnable examples and end-of-lesson challenges. Prefer it over ad-hoc example files when the goal is a structured, progressive learning repo (concepts → beginner → intermediate → advanced → testing), each with runnable code. Do NOT use this for narrated *videos* (use `tech_teacher`/bytesized-learning) — it's a written, code-first course. The whole point is that every lesson has runnable code you can modify, not just prose.
The whole point is that every lesson has *runnable code you can modify*, not just
prose. This skill covers the authoring pattern, the progression structure, how to
discover a practice API's endpoints and auth model, and how to verify every script.

## Core authoring pattern (one lesson = 1 .md + 1 solution script)

Every chapter folder contains **three things that travel together**:

- A `*.md` lesson — plain-language explanation (why before how), code snippets,
  and a **challenge** at the very bottom. The challenge is written *into* the md
  so it's read after the lesson, not hidden elsewhere.
- A `solution_<lesson>.py` — one clean, runnable script that solves the lesson's
  core task. Comments explain *why*, not just what. No robotic "In this section we
  will explore…" fluff; write like a person explaining at the reader's side.
- (For advanced/teaching lessons) a `challenge_solution.py` — the worked answer to
  that lesson's challenge, so learners can compare their attempt.

Keep naming parallel: `reading-json.md` ↔ `solution_reading_json.py`. A learner
should always be able to guess where the answer lives.

## Progression structure (beginner → intermediate → advanced)

Order lessons so each builds on the last, and mirror that in folder order:

1. **Concepts** — no code yet (what REST is, HTTP verbs, status codes, IDE setup).
2. **Beginner** — first real call against a *public* endpoint (no auth key needed).
3. **Intermediate** — authentication + the full CRUD ladder (`x-api-key`, POST/PUT/PATCH/DELETE).
4. **Advanced** — building your own server, resilient clients (retries/timeouts/errors), pagination.
5. **Testing** — end-to-end tests with `pytest` (fixtures for base URL / key / client).

Each folder's `.md` ends with a "Next: …" pointer to the following lesson.

## Directory layout template

```
<repo>/
├── README.md                      # overview, setup (IDE/venv), how-to-use guide
├── requirements.txt               # only what the course needs
├── 01-concepts/                   # concepts, no code
│   └── rest-api-basics.md + solution_basics.py
├── 02-beginner/                   # public endpoints, no key
│   ├── your-first-request.md + solution_first_request.py
│   └── … (one pair per lesson)
├── 03-intermediate/               # x-api-key CRUD ladder (one pair per lesson)
├── 04-advanced/                   # server, resilient client, pagination (one pair per lesson)
└── 99-resources/                  # cheatsheets, glossary (pure .md)
```

## Before writing a single line: discover the practice API

Many courses use a free "practice" API (e.g. `restful-api.dev`, a fake phone store).
Its real shape is rarely obvious — see the reference for enumeration + auth-model
techniques. Two things to nail down first, because beginners depend on them:

1. **Which endpoints are truly public** (no key) vs. which require auth headers.
2. **How a beginner actually obtains the key** — some practice APIs gate even their
   `/register` and `/login` behind a header, forcing you to fetch the key by hand.
   Teach that "get it once, outside code" step explicitly and load the key from an
   environment variable (never hard-code it, never commit it to Git).

See `references/api-discovery-and-auth-patterns.md`.

## Verify every script before committing

A course is only as good as the code that runs. Before you commit, run every
`.py` through both checks — see `scripts/test_course_scripts.py`:

1. **Syntax check** every script (`py_compile`) to catch typos/indent errors fast.
2. **Run each script** and confirm exit code 0, with no API key set in the process
   so auth-guarded scripts fail *gracefully* (print a hint, exit 0) instead of
   crashing or hitting the network.

Public-endpoint scripts should actually hit a live endpoint and return sensible
data; auth-guarded ones must skip cleanly without the key. Fix anything that isn't
green before committing — a course with non-running examples is worse than none.

## Pitfalls to avoid

- Don't hand-build JSON strings with `str()`; always use `requests(..., json=...)`.
- Check `response.status_code` before trusting any response body. Never trust a non-200 payload.
- Read fields with `.get("key", default)` instead of `obj["key"]` so missing keys
  don't crash the lesson.
- Don't print or commit secrets (API keys, tokens) — only their length as a sanity check.
- Don't leave README "What you will learn" or test sections pointing at chapters/lessons that don't exist yet.
