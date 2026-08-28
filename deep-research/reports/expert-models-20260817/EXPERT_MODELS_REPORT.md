# Expert Models That Beat Frontier LLMs on Specific Tasks

**Research date:** 2026-08-16/17
**Scope:** Small/specialized models that outperform frontier LLMs (GPT, Claude, Gemini, DeepSeek) on narrow, well-defined tasks.

---

## 1. Cisco Antares (350M / 1B) — Vulnerability Localization (CWE)

- **Task:** Given a vulnerability advisory, point analysts to the source files most likely to hold the known vulnerability inside real codebases.
- **Size:** 350M and 1B open-weight models (3B coming).
- **Why it wins:** Purpose-trained on vulnerability localization; runs on-premises keeping sensitive source code in-house. Cheaper per job than cloud frontier models.
- **Source:** Cisco Foundation AI, released July 2026. HF: `fdtn-ai/antares-1b`.

## 2. VibeThinker-1.5B / 3B — Verifiable Reasoning (Math, Logic, STEM)

- **Task:** Mathematical reasoning, competitive programming, STEM reasoning, instruction-following with explicit constraints.
- **Size:** 1.5B and 3B dense models (built on Qwen2.5-Coder-3B).
- **Why it wins:** "Spectrum-to-Signal Principle" post-training (curriculum SFT + multi-domain RL + offline self-distillation). 1.5B surpasses DeepSeek R1 (400× larger) on AIME24 (80.3 vs 79.8), AIME25 (74.4 vs 70.0), HMMT25 (50.4 vs 41.7). Beats Claude Opus 4 and Magistral Medium. Training cost: $7,800.
- **Source:** WeiboAI, arXiv 2511.06221.

## 3. Chandra OCR 2 (4B) — OCR / Document Parsing

- **Task:** OCR, tables, forms, math, complex layouts, multilingual document extraction.
- **Size:** 4B params (down from 9B in v1).
- **Why it wins:** 85.9% on olmOCR benchmark (SOTA), 77.8% avg on top 43 languages, 2 pages/sec on H100, 15+ block types with bounding boxes. Beats frontier VLMs on raw text extraction.
- **Source:** Datalab, HF: `datalab-to/chandra-ocr-2`.

## 4. PP-OCRv6 (34.5M) — OCR on Real-World Photos

- **Task:** OCR on photographs (labels, handwritten notes, screenshots, signs) — not just clean PDFs.
- **Size:** ~34.5M params, runs on laptop CPU.
- **Why it wins:** Reported to beat Qwen3-VL-235B, GPT, and Gemini on standard OCR benchmarks. In real-world photo tests, beats frontier VLMs on accuracy.
- **Source:** PaddlePaddle family.

## 5. Mistral OCR 4 — Document OCR

- **Task:** Document OCR at scale.
- **Why it wins:** Topped every OCR benchmark; processes up to 2000 pages/min; outperforms Google Document AI, Azure OCR, Gemini, GPT-4o on OCR benchmarks (94.89 overall).
- **Source:** Mistral AI.

## 6. OLMOCR 2 — Open-Source OCR

- **Task:** Document OCR.
- **Why it wins:** Open-source model that topped commercial OCR benchmarks; layout-aware VLM.
- **Source:** Allen Institute for AI.

## 7. Atla Selene Mini (8B) — LLM-as-a-Judge / Evaluation

- **Task:** General-purpose evaluation (absolute scoring, classification, pairwise preference).
- **Size:** 8B.
- **Why it wins:** Highest-scoring 8B generative model on RewardBench, surpassing GPT-4o and specialized judges. Outperforms GPT-4o-mini and top small judges across 11 out-of-distribution benchmarks. Dramatically improved zero-shot agreement with human experts on financial and medical tasks.
- **Source:** Atla AI, arXiv 2501.17195.

## 8. GLM 5.2 (Zhipu AI) — IDOR / Web Vulnerability Detection

- **Task:** IDOR (Insecure Direct Object Reference) detection in code.
- **Why it wins:** 39% F1 on Semgrep's IDOR benchmark, beating Claude Code (32%) at ~$0.17 per vulnerability found. Beat Claude Opus 4.8 among prompt-only models.
- **Source:** Semgrep blog, 2026.

## 9. Novee 4B — Offensive Security / Live-Browser Exploitation

- **Task:** Constrained web exploitation challenges validated in a live browser.
- **Size:** 4B proprietary.
- **Why it wins:** ~90% accuracy vs Claude Sonnet 4 at 64% — a 50% performance gap. Purpose-trained for offensive security.
- **Source:** Novee Labs, Dec 2025.

## 10. ether0 (24B) — Chemistry / Drug Design

- **Task:** Scientific reasoning in chemistry, particularly designing drug-like molecules.
- **Size:** 24B open-weights.
- **Why it wins:** Trained specifically on chemistry tasks; takes natural language questions, reasons, and outputs molecular designs.
- **Source:** FutureHouse.

## 11. Qwen3.5-9B — Document VQA / KIE / Text Extraction

- **Task:** Document question-answering, key information extraction (invoices, dates, amounts), raw text extraction.
- **Size:** 9B.
- **Why it wins:** On IDP leaderboard: 78.1 on OlmOCR text extraction (beats Gemini 3.1 Pro 74.6, Claude Sonnet 4.6 74.4, GPT-5.4 73.4). 79.5 on VQA (second only to Gemini 3.1 Pro, beats GPT-5.4). 86.5 on KIE (matches Gemini 3.1 Pro).
- **Source:** idp-leaderboard.org.

## 12. Qwen3.5-4B — Document Text Extraction / KIE

- **Task:** Document text extraction, KIE.
- **Size:** 4B.
- **Why it wins:** 77.2 on OlmOCR text extraction (beats all frontier models), 86.0 on KIE (matches GPT-5.4, beats GPT-5-Mini, Claude Haiku, Ministral-8B).
- **Source:** idp-leaderboard.org.

## 13. Qwen 3 0.6B — Simple Math

- **Task:** Simple arithmetic/equation solving.
- **Size:** 0.6B (~500MB).
- **Why it wins:** In testing, solves simple equations (e.g., 5.9 = x + 5.11) every time while GPT-5 fails 30-40% of the time without thinking mode.
- **Source:** Reddit r/LocalLLaMA.

## 14. DeepSeek V3.2 Speciale — Hard Math (IMO-level)

- **Task:** Very hard math problems (IMO P6 ballpark).
- **Why it wins:** Dominates private math benchmarks while being ~15× cheaper than GPT-5.1 High. Claude models consistently underperform on math.
- **Source:** Reddit r/LocalLLaMA.

## 15. Ornith-1.0-9B — Agentic Coding

- **Task:** Agentic coding, SWE-bench.
- **Size:** 9B dense (Qwen3.5 family).
- **Why it wins:** 69.4% SWE-Bench Verified, 80% HumanEval/MMLU/TruthfulQA, 93.3% GSM8K. 262K native context. Optimized for agentic coding.
- **Source:** DeepReinforce AI, HF: `ornith-ai/Ornith-1.0-9B`.

## 16. KAT-Coder-V2.5-Dev — Coding

- **Task:** Coding, SWE-bench.
- **Why it wins:** 70.6% SWE-Bench Verified (top local coding model for Mac in 2026). Qwen3.6-35B-A3B fine-tune.
- **Source:** Kwaipilot.

## 17. Cursor Composer 2 (Kimi K2.5) — Real-World Coding

- **Task:** Real-world coding task completion across large codebases.
- **Size:** 1T+ params (Kimi K2.5).
- **Why it wins:** 61.3 on CursorBench (surpasses Claude Opus 4.6), 61.7 on Terminal-Bench 2.0 (vs Opus 4.6 at 58.0), 73.7 on SWE-bench Multilingual. Purpose-built coding model in partnership with Cursor.
- **Source:** Digital Applied, Mar 2026.

## 18. Thinking Machines Lab + Bridgewater Custom Model — Financial Tasks

- **Task:** Real-world financial tasks (expert judgment).
- **Why it wins:** Outperformed GPT, Claude, and Gemini on financial tasks at 13.8× lower cost. Custom-trained on expert judgment.
- **Source:** Flowtivity, July 2026.

## 19. AgentFlow 7B — Agentic Workflows

- **Task:** Complex multi-turn agentic benchmarks.
- **Size:** 7B.
- **Why it wins:** Decomposes into Planner, Executor, Verifier, Generator modules with Flow-GRPO training. Outperforms GPT-4o on complex agentic benchmarks.
- **Source:** LinkedIn/AgentFlow research.

## 20. Chroma Context-1 — RAG / Multi-Hop Retrieval

- **Task:** Multi-hop retrieval, agentic search.
- **Why it wins:** Specialized RAG model that handles multi-hop retrieval chains where single-stage pipelines fail. Purpose-built for retrieval-augmented generation.
- **Source:** Chroma Research.

## 21. Friendli Tools + Llama 3 70B — Function Calling

- **Task:** Function calling / tool use.
- **Size:** 70B.
- **Why it wins:** With Friendli Tools, performs on par with GPT-4o and Fireworks Firefunction v2, excelling in complex "parallel multiple" function calling.
- **Source:** FriendliAI, July 2024.

## 22. Fine-Tuned BERT-style LLMs — Text Classification

- **Task:** Sentiment, approval/disapproval, emotions, party positions classification.
- **Why it wins:** Fine-tuned small LLMs consistently and significantly outperform larger zero-shot prompted models (ChatGPT GPT-3.5/GPT-4, Claude Opus) across all classification tasks tested.
- **Source:** arXiv 2406.08660.

## 23. Swiss-Bench Open-Weight Models — Swiss Legal/Regulatory

- **Task:** Swiss regulatory compliance (FINMA, Legal-CH, EFK), trilingual (German, French, Italian).
- **Why it wins:** Open-weight models in the top tier (35-38% correct) alongside closed frontier models on a hard legal benchmark. Top model: Qwen 3.5 Plus at 38.2%.
- **Source:** arXiv 2603.23646.

## 24. Gemini 3.1 Flash-Lite — Cost-Effective High-Volume Inference

- **Task:** High-volume inference, real-time chat, autocomplete, streaming code gen.
- **Why it wins:** $0.25/M input tokens (37.5% cheaper than GPT-5 Mini), 82.4% MMLU, 2.5× faster than Flash, 1M token context. 180ms first-token latency, 3,200 tok/s throughput.
- **Source:** Digital Applied.

---

## Key Patterns

1. **Narrow task specialization beats general intelligence.** Models trained on one task (OCR, vulnerability detection, math, chemistry) consistently outperform generalists on that task.
2. **Size is not the deciding factor.** 34.5M-param PP-OCRv6 beats 235B VLMs on OCR; 1.5B VibeThinker beats 671B DeepSeek R1 on math.
3. **Purpose-trained > zero-shot.** Fine-tuned small models beat zero-shot frontier models on classification, extraction, and structured tasks.
4. **Cost advantage is massive.** 13.8× cheaper (Bridgewater), 15× cheaper (DeepSeek math), $0.17/vuln (GLM 5.2).
5. **On-premises/private deployment** is a major driver for security and regulated industries (Cisco Antares, Novee).
6. **Post-training methodology matters more than architecture.** Spectrum-to-Signal (VibeThinker), Flow-GRPO (AgentFlow), curriculum RL all unlock frontier-level performance in small models.
