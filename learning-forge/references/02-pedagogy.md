# Stage 2 — Pedagogy: build pedagogy.json

You are now the course designer, not the researcher. Read `research/pages.json`
(top ~12 pages are enough — skim titles first, then read the 5 richest).

## Schema (contracts/pedagogy.schema.json)
```json
{
  "topic": "Decorators in Python",
  "audience": "Python developers who use @ but never read the docs",
  "prerequisites": ["functions", "calling functions", "closures (nice to have)"],
  "objective": "After this, the viewer can write their own decorator and explain what @ actually does.",
  "misconceptions": [
    {"id": "mc1", "belief": "@ is a special built-in that replaces the function",
     "reality": "it is sugar for  assignment: func = decorator(func)",
     "source": "https://docs.python.org/..."},
    {"id": "mc2", "...": "..."}
  ],
  "analogies": [
    {"id": "an1", "analogy": "bouncer at a nightclub door",
     "maps_to": "wrapper checks input before calling the original",
     "why_it_works": "people have been vouched in and out of doors a thousand times",
     "where_it_breaks": "the bouncer never changes WHO you are; a decorator CAN change behavior"}
  ],
  "examples": [
    {"id": "ex1", "title": "a 5-line timing decorator",
     "code": "@\ndef timed(fn):\n ...",
     "demonstrates": "closure + call forwarding, the core of every decorator"}
  ],
  "visualizable_moments": [
    "the @ line morphing into func = timed(func)",
    "a function entering a wrapper box and coming out stamped with a timer"
  ],
  "claims": [
    {"id": "cl1", "claim": "decorators were introduced in Python 2.4 via PEP 318",
     "source": "https://peps.python.org/pep-0318/"}
  ],
  "sources": [
    {"id": "s1", "url": "...", "title": "...", "authority": 3}
  ]
}
```

## Construction rules (the critic checks these)
- **≥3 misconceptions**, each with a sourced reality. Mine them: search the pages
  for "common mistakes", "why not", "no, actually", "it's not".
- **≥2 analogies** AND every analogy must state `where_it_breaks`. A retired
  analogy ("…but here the analogy breaks") is a re-hook, not a weakness.
- **≥1 worked example** with real, runnable, minimal code. Prefer the simplest
  correct version found in the sources over the fanciest.
- **≥3 claims** that the script can cite. Claims are atomic: one fact each,
  phrased the way you would say them out loud.
- **≥3 sources**, authority-sorted. Every misconception/reality and every claim
  must reference a source id.
- `objective` is a DOING, not a knowing: "can write / can explain / can spot".

## Quality bar (self-check before stage 3)
Read the file aloud. If you would not put it in front of a teaching team, it is
not done. Weak signals: analogies with no break point, claims without sources,
an objective that says "understand" without a verb.

## Reuse
If `projects/<slug>/pedagogy.json` already exists and the topic is unchanged,
reuse it — do not re-research for every format. One research+pedagogy run feeds
pulse AND lesson AND deep_dive for the same topic.
