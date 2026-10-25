---
name: ming-image-mac
description: "Generate images with the Ming-Image 0.1 Design model on Apple Silicon Mac via a Swift/MLX CLI (MingImageT2I). Text-to-image for UI, infographics, and posters with RGBA transparent output. Runs natively on Metal/MLX."
version: 1.0.0
author: [mkanavi]
license: MIT
platforms: [macos]
compatibility: "Apple Silicon Mac (M-series, e.g. M4 Max 64GB). Requires `swift` build toolchain and the ming-image-swift port."
prerequisites:
  commands: ["swift"]
metadata:
  hermes:
    tags:
      - image-generation
      - mlx
      - apple-silicon
      - ming-image
      - swift
      - creative
    category: creative
---

# Ming-Image on Mac (Swift/MLX)

Runs **inclusionAI/Ming-Image-0.1-Design** on Apple Silicon via a Swift port
(`github.com/xocialize/ming-image-swift`) + an `mlx-community` quantized
checkpoint. Produces UI/infographic/poster images with **RGBA transparent**
output — no CUDA, pure Metal/MLX.

## Why this path (not ComfyUI)

The original INT4 checkpoint uses a custom 3-part quantized layout with **no
working ComfyUI loader** for this format, and the upstream `MingImageDesign`
node is CUDA-targeted. This Swift+MLX port runs it natively on macOS with no
GPU needed — the correct approach for a Mac Studio.

## Model tiers (pick by RAM)

| Tier | HF repo | Size on disk | Mac fit |
|------|---------|--------------|---------|
| bf16 | `mlx-community/Ming-Image-0.1-Design-bf16` | ~96 GB | 24GB+ Macs w/ swap, heavy |
| **8-bit** | `mlx-community/Ming-Image-0.1-Design-8bit` | ~28 GB | best quality for 64GB Macs |
| **4-bit** | `mlx-community/Ming-Image-0.1-Design-4bit` | ~19 GB | comfortable on 64GB (slightly softer text) |

Download with the hf-fast-download skill:
```bash
~/.hermes/skills/machine-learning/hf-fast-download/scripts/hf_fast_download.sh \
  mlx-community/Ming-Image-0.1-Design-4bit
```
Stores to `~/.lmstudio/models/Ming-Image-0.1-Design-4bit/`.

## Build the CLI (one-time)

The port ships a library + test gate only. Add an executable target
`MingImageT2I` to `Package.swift`:

```swift
.executableTarget(
    name: "MingImageT2I",
    dependencies: ["MingImage", "MLXMingImage"],
    path: "Sources/MingImageT2I"
)
```

`MingImageT2I/main.swift` drives the core pipeline and writes an RGBA PNG.

Build with a toolchain that has a working **metal** compiler:
```bash
swift build -c release --toolchain /tmp/mytc   # mytc symlinks real metal/air
swift run MingImageT2I --help
```

If `xcodebuild -downloadComponent MetalToolchain` was needed and Xcode's
default toolchain can't locate the real compiler, build with a custom
toolchain dir (see troubleshooting).

## Run text-to-image

```bash
swift run MingImageT2I \
  --prompt "a mobile app onboarding screen with a monstera leaf and Get Started button" \
  --root ~/.lmstudio/models/Ming-Image-0.1-Design-4bit \
  --width 1024 --height 1024 \
  --seed 42 --steps 12 \
  --out ./output.png
```

- Output is a transparent-background RGBA PNG (1024x1024 or 2048x2048).
- ~60–70s per image at 1024² on a 64GB Mac Studio.
- `--seed -1` for random; keep fixed seeds (e.g. 42) for reproducibility.

## Reference prompts by use case

- UI/UX: "mobile onboarding screen, monstera leaf illustration, Get Started button"
- Infographic: "clean data infographic with charts and labels on light card"
- Poster: "bold poster layout, headline text, abstract geometric shapes"

## Educational slides (teaching real code)

The model renders ONE short line of code cleanly but garbles multi-line / complex
syntax and decorative prompts. Use minimal prompts ("a white educational slide showing the Python code <line>")
and overlay real text in a deck when legibility matters. See `references/educational-slides.md` for the full lesson and checklist.

## Troubleshooting

- **Build fails at `.metal` shader compile** — Metal Toolchain missing. Run
  `xcodebuild -downloadComponent MetalToolchain` then build with a toolchain
  dir that resolves to the real metal binary.
- **`ModuleNotFoundError: No module named 'sqlalchemy'`** — unrelated to this;
  a ComfyUI issue, ignore.
- **Softer text / lower board scores** — expected on 4-bit; switch to the
  **8-bit tier** for transparent-background assets (matches bf16 quality on a
  64GB Mac).
