# Character-prompt format + per-character seeds

Notes for the `cinematographer` plan-mode pipeline (used by movie-maker). Describes how
character consistency is achieved offline.

## The canonical character prompt format

`disney-character-creator`'s `build_prompt.py` produces a **canonical text-to-video prompt** per
character. Its layout looks like this (newlines shown as `\n`):

```
# Video Prompt — Hare\n
\n
Character:\n
Hare, a small clever hare. Wearing a simple, neutral outfit. Personality: curious, brave, kind.\n
\n
Setting: a simple, softly lit background that keeps focus on the char...
```

Key facts (verified empirically):

- The line `# Video Prompt — <Name>` is a **markdown header**, NOT the descriptor.
- The literal line `Character:` sits on its own line with **nothing after the colon**.
- The actual descriptor text (e.g. `Hare, a small clever hare...`) is on the **next non-empty
  line**, not after `Character:`.

So you cannot get the descriptor by splitting on `":"` (that yields an empty string) or by taking
the first line of the prompt.

## How cinematographer extracts it: `_extract_descriptor()`

`scripts/scene_assembly.py::_extract_descriptor(canonical_prompt)`:

1. Split into lines, strip each.
2. Find the line matching `^character\s*:?\s*$` (case-insensitive, standalone label).
3. Return the **next** non-empty line that does not start with `#`.
4. Fallback: first non-empty, non-header line that isn't a bare `character/setting/mood:` label.

Use this helper everywhere you need the descriptor (video-prompt injection AND
`visual_description`) — do not inline a different extraction in each spot.

## Per-character seeds (consistency bookkeeping)

Consistency across scenes = reuse one canonical prompt + **one fixed seed** per character. The
seed is NOT computed from the plan (plan characters have no `seed` field).

In `assemble_scenes()` (`scripts/scene_assembly.py`):

```python
import characters as _chars  # local import avoids a top-of-file cycle at rest
char_prompt_by_name = {}
char_seed_by_name = {}
for c in plan.get("characters", []):
    name = (c.get("name") or "").strip()
    if not name:
        continue
    char_obj, slug, errs = _chars.reuse_or_create({"name": name, "description": c.get("description", "")})
    vp, seed = _chars.canonical_prompt_for(char_obj, slug)   # real per-character seed
    char_prompt_by_name[name] = vp
    char_seed_by_name[name] = seed                           # NOT a hash / not 100
```

Then per scene: `"seed": char_seed_by_name.get(subject) or _first_seed(plan)`.

`_first_seed(plan)` is still a safe fallback (returns `None` when no character has a seed), but the
primary path must use the real per-character seed captured above. A scene whose `seed` is always
`100` means the fallback fired — the real seed was never captured.

## `characters.py` surface (import from scene_assembly)

- `reuse_or_create({"name", "description"})` → `(character_json, slug, errors)`. Loads an existing
  `disney-character-creator` character.json if the slug matches and validates, else synthesizes one.
- `canonical_prompt_for(character_json, slug)` → `(video_prompt_text, seed)`. Uses
  `disney-character-creator`'s build_prompt engine so wording matches its conventions.
