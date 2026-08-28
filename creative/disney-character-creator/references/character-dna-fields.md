# Character DNA Fields (and Why Each Matters)

Every field below must be **gathered from the user**, never assumed. Pixar-style characters are
emotion-driven, so personality and story carry as much weight as physical appearance — a design
that ignores character interiority looks like "generic 3D render," not Disney/Pixar.

## Identity (who they are)
- **name** — anchors the whole character; drives how you describe them in every prompt.
- **species** — a *descriptive phrase*, not a bare category label. Write it as you'd say it in
  a prompt: `"a small weathered robot with rounded body and stubby limbs"` or `"a young
  anthropomorphic field mouse"`. This is the single most important visual choice — it sets body
  plan, material (metal vs fur), and silhouette. A bare word like "robot" is too vague for the
  renderer to work from. (Required.)
- **appearance_age** — how old they *look*, not necessarily their real age. Determines proportion
  of features (kids = bigger head/eyes, smaller bodies).
- **gender** — if relevant to how they present.

## Personality & Story (what makes them a *character*)
- **traits[]** — 3 core traits. Pixar characters are built around a clear personality; three
  concrete adjectives (e.g. *curious, stubborn, kind*) give the renderer and video prompt
  emotional texture to aim for. (Required.)
- **motivation** — what they want more than anything. Drives action in video prompts and keeps
  the character "alive" across shots. (Required.)
- **flaw_or_arc** — their emotional flaw or growth arc. This is the heart of Pixar storytelling
  (Toy Story's Woody, Inside Out's Joy, etc.). Include it so the video prompt can carry
  emotional weight. (Required.)

## Physical Appearance (how they look)
- **body_proportions** — head-to-body ratio, overall build. Pixar leans toward *large head +
  large body* (younger = bigger head). Describes the silhouette. (Required.)
- **face_shape** — round, heart-shaped, long, etc. Round faces read as younger/softer/more
  appealing (the "baby schema" effect). (Required.)
- **eyes** — *size* and *color*. Research finding: **oversized, expressive eyes are a defining
  Pixar trait.** Don't skip size — specify it. (Required.)
- **hair_color_texture_style** — color, texture (straight/wavy/curly/spiky), and style. For
  non-human characters, this maps to fur, feathers, bark texture, etc. (Required.)
- **skin_tone** — for human/anthropomorphic characters; also the base material tone for
  objectified creatures (e.g. weathered metal). (Required.)
- **relative_height** — how tall relative to a standard human reference. Adds variety and helps
  the character read distinctly in group shots / video prompts.

## Wardrobe & Style (what they wear)
- **clothing[]** — top, bottom, footwear. List each item; be specific about cut and fit
  (Pixar clothing is stylized, not photorealistic). (Required.)
- **palette** — 2–4 colors. Pixar uses strong, limited color palettes for instant readability
  and silhouette recognition. (Required.)
- **signature_accessory / prop** — one defining item or weapon/tool that makes the character
  identifiable at a glance (a cape, goggles, a specific tool). This is often the most
  "characterful" element. (Required.)

## Style & Technical (for reproducibility)
- **aspect_ratio** — e.g. `16:9` (video), `4:5` or `3:4` (hero portrait).
- **render_intensity** — 0–1, how strongly to push the stylized/Pixar look (higher = more
  exaggerated). Default ~0.5. Optional; ask if unsure.
- **seed** — integer for reproducibility. May be left as a random int the user can change;
  **always record it so future shots reuse it.** (Required.)
- **model** — which FLUX variant to render with. Default `flux2-klein-9b` (quality + reliable
  multi-reference editing). Optional; the script hard-codes this.
