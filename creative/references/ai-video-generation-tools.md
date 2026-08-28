# AI Video Generation Tools — Knowledge Bank

*Compiled August 2026 from deep research on 76 sources across 78 queries.*

## Three Paradigms of AI-Generated Animation

### 1. LLM-to-Code-to-Video (Manim-Adjacent)
LLMs generate Manim Python code → Manim engine renders. Preserves mathematical precision.

| Tool | Status | Key Metric |
|------|--------|-----------|
| **LLM2Manim** (arXiv 2026) | Research | 83% vs 78% test scores vs PowerPoint |
| **Manimator** (arXiv 2025) | Open-source | Research paper PDF → animation |
| **Academa Studio** | Startup | ~40s generation, ~5 videos/month free |
| **Generative Manim** | Open-source | GPT-4o + fine-tuned GPT-3.5 |
| **AnimG** | Commercial | Claude Sonnet, browser-based, no install |
| **Kodisc** | Commercial | Claude Sonnet + plugin support (physics, chemistry, circuits, ML) |
| **ManimTrainer** (arXiv 2026) | Research | Qwen 3 Coder 30B: 94% render success, 85.7% visual similarity |
| **ANVIL** (arXiv 2026) | Research | Analogy-based learning pipeline for CS topics |

**Common failure modes:** Overlapping objects, positioning errors, code quality degradation on complex multi-scene animations, factual errors in generated explanations.

### 2. Document-to-Explainer (Template-Based)
Documents/prompts → narrated 2D animated explainers via templates + motion graphics + AI voiceover.

| Tool | Best For | Notable |
|------|----------|---------|
| **Knowlify** | Document-to-video | 200K+ videos produced |
| **Simi** | Fast prompt-to-explainer | Lamina Labs |
| **Powtoon** | 2D animated explainers | 50M+ users |
| **Synthesia** | AI avatars, corporate training | 160+ languages |
| **Renderforest** | Multi-style video | 34M+ users |
| **Pictory** | Repurposing articles to video | Stock footage + generative media |
| **InVideo** | Social media content | Stock footage + generative media |
| **Crreo** | Long-form (up to 30 min) | Up to 30-minute explainer videos |

### 3. End-to-End Text-to-Video (Generative)
Text → pixel-level video via diffusion transformers or autoregressive models.

| Model | Params | Creator | Release | Notes |
|-------|--------|---------|---------|-------|
| **Google Veo 3** | Proprietary | Google | 2025 | Scene expansion, camera controls |
| **Runway Gen-4** | Proprietary | Runway | 2025 | World consistency |
| **OpenAI Sora** | Proprietary | OpenAI | 2024 | Up to 2 min clips |
| **Kling** | Proprietary | Kuaishou | 2024 | High-quality motion |
| **HunyuanVideo** | 13B+ | Tencent | Dec 2024 | Open-weight |
| **Mochi** | 10B | Genmo | Oct 2024 | Open-weight |
| **Wan2.2** | 5B/14B | Alibaba | Jul 2025 | Open-weight |
| **PixVerse V6** | Proprietary | PixVerse | 2026 | 1080p, 15 sec, character consistency |
| **Adobe Firefly Video** | Proprietary | Adobe | 2025 | Commercially safe |
| **DomoAI** | Proprietary | DomoAI | 2025 | 30+ styles (anime, realistic, pixel) |

## Key Limitations

- **Generative T2V cannot render mathematical notation** — equations, graphs, precise geometry are unreliable
- **Character consistency** remains the "final boss" of AI video generation
- **Short clip duration** — 5-15 seconds typical; longer videos lose coherence
- **GPU requirements** — open-source models need 24GB+ VRAM
- **Temporal artifacts** — flickering, jitter, style drift across frames

## Market Stats (2026)

- AI video generator market: $788.5M (2025) → $3.44B projected by 2033
- 68% of video marketers created explainer videos in 2026 (Wyzowl)
- 96% of people have watched an explainer video to learn about a product (Wyzowl 2026)
- 13% of organizations actively building image/video generation tools (2026 Currents)

## Research Papers

1. Hayawi & Shahriar (2026). *Generative AI for Text-to-Video Generation: Recent Advances and Future Directions*. Digital, 6(1), 23.
2. LLM2Manim (2026). *Pedagogy-Aware AI Generation of STEM Animations*. arXiv:2604.05266.
3. ManimTrainer (2026). *Training and Agentic Inference Strategies for LLM-based Manim Animation Generation*. arXiv:2604.18364.
4. ANVIL (2026). *Analogies and Videos for Lecturers*. arXiv:2605.16295.
5. Manimator (2025). *Transforming Research Papers and Mathematical Concepts into Visual Explanations*. arXiv:2507.14306.
6. Manim for STEM Education (2025). *Visualizing Complex Problems Through Animation*. arXiv:2510.01187.
