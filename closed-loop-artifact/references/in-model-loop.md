# In-model closed-loop run (session that built this skill)

A live end-to-end run of the in-model loop, executed entirely by the model
running this skill (Ornith-1.5-35B-A3B-MLX-4bit via the local `omxl` endpoint
`http://127.0.0.1:1234/v1`). No `pi` coding agent, no LiteLLM/Ollama proxy,
no external model, no routing.

## Spec

SVG bar chart: 3 bars of increasing height, x-axis labels X1/X2/X3, title
"Monthly Sales" at top. `max_iters: 3`, `score_threshold: 0.8`.

## Iterations (scores from rendered pixels, not hand-waving)

| Iter | Bars increasing | X-labels present | Title at top | Overall | Verdict |
|------|-----------------|------------------|--------------|---------|---------|
| 1    | 1.0             | 1.0              | 0.0          | 0.67    | FAIL — title missing |
| 2    | 1.0             | 1.0              | 1.0          | 1.00    | PASS — stop |

Judged from actual rasterized PNGs (PIL, grayscale):
- Bar heights measured pixel-to-pixel: **121 < 221 < 341 px** (strictly increasing).
- Title detected by dark-pixel ratio in the top zone: iter1 = **0.0000** (no title),
  iter2 = **0.0488** (title present). Threshold ratio 0.002.
- X-labels X1/X2/X3 confirmed by scanning a window around each label center.

Bar heights were measured by scanning each column in the lower band (y 20%–85%)
for the top-most ink pixel (grayscale < 160); blue bars (#2563eb ≈ 95 gray) need
a relaxed ink threshold, otherwise they read as background.

## Routing lesson (why the loop is in-model)

The theloop package's `pi` coding agent is hardcoded to reach **Ollama** (not the
LiteLLM proxy). When Ollama is unreachable, `pi` fails with:

    pi exited before new_session response
    [pi-ollama] Ollama not reachable ... Model "Ornith-1.5-35B-A3B-MLX-4bit" not found

So the loop cannot depend on `pi` or any external model. The correct approach:
**the executing model runs the loop itself** — plan, write the artifact, render
to PNG, judge against the spec (anchored to real pixels via
`scripts/verify_artifact.py`), and iterate until the threshold is met. This is
what the `closed-loop-artifact` skill prescribes.

## Artifacts

iter1.svg / iter1.png (no title, score 0.67), iter2.svg / iter2.png (title
added, score 1.0), spec.json, judgment.json — all written under
`runs/theloop-inmodel/`.
