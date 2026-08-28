---
name: creative
description: >
  Broad creative tools umbrella: ASCII art/video, HTML sketches & mockups, SVG diagrams,
  Excalidraw diagrams, generative art, video creation, and design system replication.
  Covers text-based art, HTML/CSS artifacts, and visual design prototypes.
version: 1.0.0
author: Hermes Agent
tags: [creative, ascii, html, svg, diagrams, sketches, generative-art, design]
---

# Creative Tools

**Umbrella for creative output: ASCII art, HTML mockups, SVG diagrams, Excalidraw, and generative art.**

## Table of Contents

- [1. ASCII Art & Video](#1-ascii-art--video)
- [2. HTML Sketches & Mockups](#2-html-sketches--mockups)
- [3. SVG Architecture Diagrams](#3-svg-architecture-diagrams)
- [4. Excalidraw Diagrams](#4-excalidraw-diagrams)
- [5. Generative Art & Interactive Sketches](#5-generative-art--interactive-sketches)
- [6. When to Use Each Tool](#6-when-to-use-each-tool)

---

## 1. ASCII Art & Video

### ASCII Art (`ascii-art`)

Generate ASCII art banners, character art, and borders.

- **Tools**: `pyfiglet`, `asciified`, `cowsay`, `boxes`
- **Constraint**: Monospace, max width 60 chars
- **Load when**: "create ASCII art", "banner for terminal"

### ASCII Video (`ascii-video`)

Convert video/audio to colored ASCII MP4/GIF.

- **Stack**: Python, NumPy, SciPy, Pillow, ffmpeg
- **Standard**: High aesthetic ambition. "First-render excellence."
- **Load when**: "convert video to ASCII", "ASCII art animation"

---

## 2. HTML Sketches & Mockups

### Sketch (`sketch`)

Quick HTML mockups: 2-3 design variants to compare.

- **Workflow**: Rapid iteration, compare multiple approaches
- **Load when**: "mock up a UI", "design a page", "create HTML prototype"

### Popular Web Designs (`popular-web-designs`)

54 real design systems (Stripe, Linear, Vercel) as HTML/CSS templates.

- **Use**: Replicate the look of a specific website
- **Load when**: "make it look like Stripe", "design like Linear"

### Claude Design (`claude-design`)

Design process and taste: scoping a brief, producing variants, verifying artifacts, avoiding AI-design slop.
- **Deck extension**: HTML slide decks with keyboard nav, built from existing templates or from scratch. See `claude-design` skill for Deck Rules.
- **Use**: For the design *process* — pair with `popular-web-designs` for visual vocabulary
- **Load when**: "design a landing page", "create a UI mockup", "build a presentation deck"
- **Load when**: "design a landing page", "create a UI mockup"

---

### SVG Architecture Diagrams

### Architecture Diagram (`architecture-diagram`)

Dark-themed SVG architecture/cloud/infra diagrams as single HTML files.

- **Constraint:** No external tools/APIs. Pure HTML/SVG inline CSS.
- **Design System:** Semantic color mapping (Cyan=Frontend, Emerald=Backend, etc.)
- **SVG color pitfall:** In HTML slide decks, CSS `var(--*)` does NOT work reliably for SVG `<rect fill>`, `<line stroke>`, or SVG `<marker>` colors. Use explicit hex/rgba in SVG attributes, or define CSS classes and apply via SVG `class` attribute. Always verify SVG rendering with `browser_vision` — it often breaks silently.
- **Load when:** "draw a system architecture diagram", "cloud architecture SVG"

See also: `claude-design` references/template-selection-svg-pitfalls.md for SVG color rendering in presentation decks.

---

## 4. Excalidraw Diagrams

Create hand-drawn style diagrams via JSON files.

- **Constraint**: Text must use `boundElements`/`containerId`; `label` property on shapes is forbidden
- **Workflow**: Write JSON → Save `.excalidraw` file → Optional upload for shareable link
- **Load when**: "draw a diagram", "Excalidraw sketch"

---

## 5. Generative Art & Interactive Sketches

### Generative Art
Create algorithmic art using Perlin noise, cellular automata, and other generative techniques.

- **Stack**: Python-based
- **Standard**: High aesthetic ambition. Reproducible output.
- **Load when**: "generate generative art", "create algorithmic art"

### p5.js Sketches (`p5js`)
p5.js sketches: generative art, shaders, interactive sketches, and 3D rendering.

- **Use**: Browser-based interactive creative coding
- **Load when**: "create interactive sketch", "p5.js art", "generative shader"

---

## 6. When to Use Each Tool

| Need | Tool | Category |
|------|------|----------|
| Terminal banner | `ascii-art` | ASCII |
| Video to ASCII | `ascii-video` | ASCII |
| Quick UI mockup (2-3 variants) | `sketch` | HTML |
| Replicate Stripe/Linear look | `popular-web-designs` | HTML |
| Design process guidance | `claude-design` | Design |
| System architecture diagram | `architecture-diagram` | SVG |
| Hand-drawn style diagram | `excalidraw` | Diagram |
| Algorithmic/generative art | `creative` (generative art) | Art |

---

## Cheat Sheet & Reference Document Templates

Quick-start templates for educational/reference HTML documents with usage blocks, code examples, and practice problems.

- **Light template** (`templates/python-cheatsheet-template-1.html`): Clean card layout, indigo accents, Inter + JetBrains Mono. Best for print/PDF export.
- **Dark template** (`templates/python-cheatsheet-template-2.html`): Cyan glow accents, DM Sans + Fira Code. Best for digital reading.
- **Structure**: Section header → Usage block → Code example → 2 practice problems with hints
- **Load when**: "build a cheat sheet", "create study guide", "reference document with examples"

### HTML Artifact Workflow

1. Design the layout in your head (or load a template from `popular-web-designs` or `templates/python-cheatsheet-template-X.html`)
2. Write the HTML/CSS using `write_file`
3. Verify with `browser_vision` to check visual accuracy
4. Serve with `cloudflared` tunnel if the user needs to see it remotely

### Diagram Workflow

1. Describe the system/diagram to the agent
2. Agent generates the diagram (SVG, JSON, or HTML)
3. Save to file
4. Open in browser (for HTML/SVG) or import to Excalidraw viewer (for JSON)

---

## AI Video Generation Tools

When the user asks about AI-powered video/animation generation (text-to-video, animated explainers, Manim alternatives), load `references/ai-video-generation-tools.md` for a condensed knowledge bank of tools, models, and capabilities across three paradigms:

1. **LLM-to-Code-to-Video** (Manim-adjacent): LLM generates Manim Python code → Manim renders. Preserves mathematical precision. Best for STEM/math content.
2. **Document-to-Explainer** (template-based): Documents/prompts → narrated 2D animated explainers. Best for corporate training, marketing.
3. **End-to-End Text-to-Video** (generative): Text → pixel-level video via diffusion. Best for cinematic clips, social media.

**Critical limitation:** Generative T2V models cannot reliably render mathematical notation, equations, or precise geometry. For STEM/math content, LLM-to-Manim approaches are the only viable option.

See also: `manim-video` skill for Manim CE animation production pipeline.

## Pitfalls

- **ASCII art width**: Always respect the 60-char monospace constraint
- **Excalidraw text**: Never use `label` property — always use `boundElements` with `containerId`
- **HTML verification**: Always use `browser_vision` to verify HTML artifacts render correctly
- **SVG constraints**: Architecture diagrams must be self-contained — no external CSS/JS
