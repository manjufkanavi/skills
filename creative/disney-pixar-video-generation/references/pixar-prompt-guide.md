# Disney/Pixar Prompt Guide (for the disney-pixar-video-generation skill)

Condensed from `deep-research/markdown/disney-pixar-style-video-generation.md`. This is the
knowledge base `enrich_prompt.py` draws from. Read this when adjusting look terms, gap-fill
defaults, or the template order.

## The "Pixar Look" — what actually defines it

The look is roughly **70% lighting + render-engine terms** and ~30% character design. Models
respond far better to concrete rendering language than to the abstract phrase "looks like Pixar."

| Feature | Prompt cue |
|---|---|
| Soft global illumination | `warm volumetric lighting`, subsurface scattering |
| Rounded, exaggerated proportions | soft rounded shapes, stylised anatomy |
| Glossy / subsurface materials | `subsurface scattering`, glossy skin, matte fabric |
| Warm painterly haze | `cinematic colour grading`, warm palette |
| Clean high-detail render | `octane render`, `Unreal Engine 5 style`, ray-traced reflections |
| Studio feel (copyright-safe) | `Disney-style 3D animation`, `Pixar aesthetic` — describes *properties*, not a named studio |

## Winning prompt structure (layered, in order)

```
[SUBJECT + ACTION] → [CHARACTER DETAILS] → [ENVIRONMENT/SCENE]
→ [LIGHTING / RENDER TERMS] → [CAMERA / MOTION] → [STYLE LOCK]
```

Example (on-style):

> A small fox character with a red scarf runs across a meadow at golden hour, oversized expressive
> eyes, soft fur with subsurface scattering, warm volumetric lighting, octane render, Unreal Engine
> 5 style, cinematic colour grading, shallow depth of field, Disney-style 3D animation, Pixar
> aesthetic, soft rounded shapes, film grain, 24fps.

## Gap-fill rules (neutral defaults — never fabricate specific detail)

A field is treated as **well defined** only when it has real descriptive content (roughly ≥15
chars, 2+ meaningful words). Short/vague/empty input gets a **neutral** default so the user can
override by supplying real detail:

| Field | Neutral default (used when input is vague/missing) |
|---|---|
| character | `a person` |
| scene / environment | `a plain, softly lit room` |
| action (subject + motion) | `standing with calm, subtle motion` |

Always-append look terms (the ~70% that defines the aesthetic), applied to every prompt regardless
of input richness:

- Lighting/render: `warm volumetric lighting, subsurface scattering`, `octane render, Unreal Engine 5 style`
- Camera/motion: gentle subtle motion + shallow depth of field (keep minimal to avoid morphing)
- Style lock: `cinematic colour grading, shallow depth of field, Disney-style 3D animation, Pixar
  aesthetic, soft rounded shapes, film grain, 24fps`

## Pitfalls & fixes (from the research report)

| Problem | Fix |
|---|---|
| Character changes between shots | One ~5s hero shot; don't rely on text continuity across clips |
| Looks "cartoonish" not "Pixar" | Add `octane render` / `subsurface scattering` / warm volumetric lighting terms |
| Morphing or warping (long shots) | Keep it ~5s; reduce motion intensity; keep prompts tight |
| Style drift between clips | Append the identical style-lock block every time (built into this skill) |
| Copyright issues (2025–2026) | **Do not** prompt "in the style of [named studio]". Describe *visual properties*
instead. Output is generally not copyrightable; monetisation carries risk. |

## Practical recommendations (2026)

1. Single hero shot, best look: a detailed style prompt + tight motion.
2. Consistency ≈ constraints — the more boringly-specific your character and scene, the closer to
   "Pixar." This skill fills gaps with neutral defaults precisely because specificity drives quality.
3. Keep clips short; add slight motion only where needed to reduce morphing and style drift.

## Model families (for context; video-generation skill handles selection)

- **FastMetal-QAD** (this skill's backend): MLX-native, INT8 pre-quantized DiT.
  - `1.3b` = FastWan 2.1 T2V, 480p (~5s).
  - `5b` = Wan 2.2 TI2V, 720p (~7.5s), higher fidelity but longer render.
- Frontier closed models (Runway Gen-3, Kling 2.0, Veo) give strong aesthetics but weaker shot-to-shot
  consistency — not used here; this skill renders one single hero clip.
