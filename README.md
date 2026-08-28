# Hermes Agent Skills

A curated collection of skills for [Hermes Agent](https://hermes-agent.nousresearch.com/docs). Each skill provides specialized knowledge, workflows, and proven patterns for a specific category of task.

## Skill Index
| Skill | Purpose |
|-------|---------|
| **agent-toolkit** | Integrate graphify (knowledge graphs), headroom (tool-output compression), and mem0 (persistent memory) into the agent workflow. |
| **ansible-iac-patterns** | Convert manual Docker Compose infrastructure into Ansible-driven IaC using reusable patterns and best practices. |
| **antigravity-cli** | Harness all capabilities of the Google Antigravity CLI (`agy`) for advanced operations. |
| **apple** | Complete Apple ecosystem note-taking and task management workflows (Notes, Reminders). |
| **autonomous-ai-agents** | Spawn and orchestrate autonomous AI coding agents: multi-agent workflows, delegation, coordination. |
| **comfyui** | Unified image and video generation: Flux2-klein-9B for images via mflux, Wan 2.1 1.3B for videos via ComfyUI. |
| **computer-use** | Drive a desktop background-first; escalate on signal for GUI automation tasks. |
| **creative** | Broad creative tools umbrella: ASCII art/video, HTML sketches, and visual design. |
| **data-science** | Data science workflows: interactive exploration, Jupyter notebooks, analysis, visualization. |
| **dev-workflow** | Complete software development workflow toolkit: architecture to deployment. |
| **devops** | Infrastructure debugging, cloudflared tunnels, nginx reverse proxy setups and troubleshooting. |
| **draw-charts** | Generate charts and diagrams from data for reports or presentations. |
| **email** | Send, receive, search, and manage email from the terminal. |
| **ethical-hacking** | Ethical hacking & penetration testing with CLI tooling for security assessments. |
| **feynman** | Apply the Feynman Technique for learning and reviewing complex concepts. |
| **git-dual-remote-sync** | Set up simultaneous push to two Git remotes (e.g. GitHub + Gitea) for redundancy. |
| **gitea-infrastructure** | Gitea infrastructure management: admin password reset, auth setup. |
| **github** | Complete GitHub workflow — authentication, repository management, PRs, code reviews. |
| **hermes-configuration** | Configure and debug Hermes Agent: auxiliary providers, settings. |
| **hermes-model-switcher** | Switch between local models: list oMLX options, check RAM constraints. |
| **html-to-pdf** | Convert HTML files to PDF using WeasyPrint for reliable document generation. |
| **image_gen** | Image editing and compositing using mflux with FLUX.2 Klein models. |
| **infographic-show** | Generate narrated MP4 infographic videos from SVG scenes using a self-correcting loop. |
| **infographic-video** | Generate infographic-style videos from structured scenes; SVG cards or AI-composited real images. |
| **infographic-video-image** | Generate infographic videos entirely from AI-generated images (Flux2-klein-9B via mflux) with text overlays. |
| **infographic-video-svg** | Generate infographic videos entirely from programmatically rendered SVG cards — no downloads, no compositing. |
| **kannada-cinematographer** | Agy-powered scene creator — takes Kannada text and visualizes it as a short film, generating image prompts. |
| **kannada-essay** | Agy-powered Kannada essay generation using role-based prompting. |
| **kannada-poet-agy** | Kannada poetry pipeline using Google agy for creative generation. |
| **kannada-reel** | 60-second vertical Kannada trending reel: combines trend + voiceover. |
| **kannada-tts** | Kannada Text-to-Speech using AI4Bharat Indic-TTS (FastPitch + HiFiGAN); converts text to WAV. |
| **kannada-video-generator** | End-to-end Kannada video: essay → TTS audio → scenes → AI images → MP4 with crossfade transitions. |
| **keycloak** | Debug, configure, and maintain Keycloak in Docker Compose for auth. |
| **kokoro-tts** | Standalone text-to-speech using Kokoro ONNX model; generation and tuning. |
| **logo-animation** | Brand mascot animation: generate simple, cute character animations. |
| **machine-learning** | ML architectures and tools: segmentation (SAM), audio, image models. |
| **markitdown** | Convert PDF, PPTX, DOCX, HTML into clean Markdown for downstream processing. |
| **media** | Media processing: GIF search, YouTube transcripts, music generation, visualization. |
| **ml** | Machine learning utilities and model management helpers. |
| **mlops** | MLOps workflows: training pipelines, deployment, model management. |
| **multi-agent-orchestration** | Build and run multi-agent software development workflows. |
| **multi-model-service-audit** | Audit services across multiple AI models for consistency and quality. |
| **note-taking** | Save information, assist research, collaborate across sessions with notes. |
| **openbao-access** | Secure OpenBao CLI access and secret management: list, read secrets. |
| **openbao-production** | Single umbrella skill for all OpenBao/Vault production work. |
| **pptx-maker** | Generate a beautiful, animated, editable PowerPoint (.pptx) deck. |
| **productivity** | Document creation: Word docs, spreadsheets, PDFs, meetings. |
| **rag-pipeline** | Run RAG pipelines with local models: retriever + generation. |
| **repo-consolidation** | Analyze multiple repositories, identify patterns and consolidation opportunities. |
| **research** | Academic research: discovery, literature review, market data, monitoring (includes deep-research & tinyfish). |
| **research-evaluation** | Critical evaluation framework for assessing ML/AI research papers. |
| **retrieval-engineering** | Build, evaluate, and optimize hybrid retrieval pipelines. |
| **security** | Security workflows: secrets management, audits, compliance patterns. |
| **security-audit** | Model-driven vulnerability assessment and security auditing workflows. |
| **service-replacement** | Replace or migrate legacy services with modern alternatives safely. |
| **social-media** | Social media content creation, scheduling, and management workflows. |
| **software-development** | Software engineering: debugging, architecture, testing best practices. |
| **svg-image-generator** | Generate high-quality SVG images from natural language via a Creative Director persona; outputs SVG + JPEG. |
| **telegram-bot** | Telegram Bot development and management: polling, updates, handlers. |
| **testing** | Test orchestration: run, classify, and report test results efficiently. |
| **theloop** | Generate and refine SVG or markdown artifacts via a self-correcting loop. |
| **ux_design** | Responsive, print-friendly presentation decks (phone → laptop → desktop) across 8 color/font themes. |
| **video-gen** | Text-to-video generation using Wan 2.1 1.3B via ComfyUI; produces short MP4s from text prompts. |
| **vite** | Modern frontend build & deploy: Vite, ESM imports, best practices. |
| **voice-bridge** | Voice-to-voice communication: send voice notes to Hermes Agent. |
| **whats-trending** | Fetch trending topics (India, Karnataka, Global) via Google Trends + News RSS; stored as JSON. |
| **whats-trending-reel** | ~24-second vertical Kannada reel narrated by a teenage podcaster; uses Veo 3 video generation. |
| **whats-trending-video** | Orchestrates trends → deep research → Kannada translation → AI video. |
| **wiki-compiler** | Multi-source research workflows: search discovery, compilation into a wiki. |

## Installation

Skills are loaded automatically by Hermes Agent when relevant to a task. To use one, simply reference it in your request or configure it via `hermes skills`.

## Repository Layout

```
skills/
├── README.md          # This file — skill index and overview
└── <skill-name>/      # Individual skill directories
    ├── SKILL.md       # Core skill documentation and instructions
    └── references/    # Optional supporting reference materials
```

## Contributing

Each skill is a self-contained directory. Add a `SKILL.md` with proper frontmatter for new skills.
