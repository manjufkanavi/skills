# Pixar Aesthetic & Render Terms

Pixar look is roughly **70% lighting/render + 30% character design**. The render vocabulary
below is what actually produces the "Disney/Pixar look" — generic descriptions like *"looks like
Pixar"* are far less reliable than concrete render/lighting terms.

## Character Description Terms (the 30%)
- **Silhouette & shape language** — "clean, readable silhouette", "rounded shapes for a friendly
  character" or "angular, sharp silhouette for a villain." Strong silhouettes read instantly.
- **Proportions** — "exaggerated proportions", "large head, small body" (youthful/charming).
- **Materials** — "soft matte plastic skin", "satin fabric", "brushed metal with light scratches".
- **Expression** — "expressive, large eyes", "warm smile", "curious tilt of the head".
- **Color** — "vibrant, saturated limited palette", "warm earthy tones".

## Render / Lighting Terms (the 70%)
- **`octane render`** — a physically-based renderer that gives the clean, polished look Pixar
  films lean on. Use it to signal "high-end CG."
- **`subsurface scattering`** — the soft glow of light passing through semi-translucent surfaces
  (skin, wax, leaves). This is what makes CGI skin look alive rather than plastic.
- **`warm volumetric lighting`** — visible light rays, soft glow; adds depth and mood. A
  hallmark of Pixar interiors/exterior day shots.
- **`soft rim light`** — a back edge-light that separates the character from background.
- **`cinematic depth of field`** — blurred foreground/background to keep focus on the character.
- **`clean, soft shadows`** — no harsh black shadows; Pixar lighting is gentle.
- **`studio-quality CG`, `film still`**, **`highly detailed 3D render`** — reinforce quality.

## What to AVOID (negative terms)
- Photorealism, `hyperrealistic`, `photograph` — pushes toward live-action and kills the
  stylized look.
- `grainy`, `overexposed` — muddy output on the 9B model.
- Overcrowd the prompt: put character design first, then lighting/render terms last so they
  don't compete for attention.

## Prompt Structure (from research)
1. **Subject** — who/what the character is + pose/expression (most important, first).
2. **Costume** — clothing and signature prop.
3. **Setting / background** — optional, keep simple so it doesn't distract from the character.
4. **Lighting & render terms** — `octane render, subsurface scattering, warm volumetric
   lighting`, etc. (these do the heavy lifting for the "Pixar look").

## Sources
- disney-pixar-style-video-generation.md (deep-research report, 2026-08-29).
- cinematographer-scene-construction-story-narrative-continuity.md (deep-research report, 2026-08-29).
