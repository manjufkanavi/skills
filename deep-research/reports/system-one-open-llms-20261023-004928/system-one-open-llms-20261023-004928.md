---
topic: system-one-open-llms
source: deep-research — 36 scraped pages (TinyFish) + live HuggingFace API
date: 2026-10-23
downloads-window: HuggingFace last-30-days download counts
license-criterion: fully open source (Apache-2.0 / MIT)
---

# System One LLMs: the fully open-source models, ranked by HuggingFace downloads

## 1. Definition — what a "System One" model is

"System 1" is Daniel Kahneman's name (from *Thinking, Fast and Slow*) for the fast,
automatic, intuitive judgment faculty. **TypeSafe AI** (San Francisco; founder Diogo
Almeida, an OpenAI veteran) launched **Jev** on 15 September 2026 as the first model in
a new category it calls **"System One models"** — better described as *decision models*.

A System One model does **not generate text**. You give it:
- a **state** (any text or JSON — the application's current situation), and
- typed **questions**: `choice` (pick among up to 255 options), `score` (2–10 ordered
  levels), `noul` (yes/no probability).

It returns **calibrated probabilities** from **one forward pass** — nothing is
generated, so structured-output errors are zero by construction. Jev is named after the
Jevons paradox (make a resource cheap enough and consumption explodes), and TypeSafe
markets it at ~10 ms latency, 350+ RPS on one vCPU, 64k context.

**Jev itself is closed.** Its calibration comes from a proprietary training method
(RLCD — Reinforcement Learning for Calibrated Decisions); its size and hardware are
undisclosed; it is served only as a hosted API (independently measured 238–301 ms
median end-to-end). The open models below are independent reproductions of its *shape*.

**Mechanics (the open version of "how Jev works"):** the decision is written as a
sentence to complete; every option is scored as that completion at one token position
in a frozen or lightly tuned open backbone, then softmax-normalised into probabilities
(temperature or head-level calibration). Variants exist: LoRA + decision head on a full
LLM, projection heads on a frozen encoder (CLM), or encoder-only models (deberta,
ModernBERT).

## 2. Evolution — why open versions appeared

- Jev's sweet spot is exactly the glue logic of agents: routing, tool/action selection,
  moderation, RAG relevance, verification of other models' output, computer-use
  (which element to click). A closed API for that = cost, lock-in and data-egress
  problems — so the community rebuilt it on open backbones.
- By mid-October 2026 there were **287 open-source Jev projects** (community review),
  a curated `awesome-jev` list, a Jev-compatible local runtime (Ollaya), the
  **S1MB benchmark** (100+ models, one eval harness), and JevBench (JevK5 ranked #2 of
  76 systems: 62.04 vs Jev 1.13's 63.29).
- The main open architectures: (1) LoRA/decision-head on frozen Qwen/Gemma LLMs — the
  JEV family, JevK5, Jev-Style, guards, OpenThai, Jeva; (2) contrastive-learning heads
  on frozen encoders — CLM-8B (up to 9× lower latency than Jev, SOTA verifier on
  DeepSWE/Terminal-Bench); (3) compact encoder-only models — von (395M, CPU, 1–2 GB),
  THX-01 (322M, phone), open-jev-deberta, Laya.

## 3. The list — top 20 fully open-source System One models by HuggingFace downloads

Download counts are HuggingFace's last-30-days figures, captured 23 Oct 2026.
"Fully open source" = OSI open license (Apache-2.0 / MIT) on the released weights.
RAM = weight size at the shipped precision + ~15% runtime headroom.

| # | Model (HuggingFace) | Family | DL (30d) | Params | License | RAM needed | Response time (published) |
|---|---|---|---:|---:|---|---|---|
| 1 | `autotrust/JEV-27B-VL` | JEV (AutoTrust) | 2,171,773 | 27.8B (Qwen3.8-27B + vision) | Apache-2.0 | 56 GB bf16 (Q4 GGUF ≈ 17 GB) | ~264 ms/row (RTX PRO 6000); 1.15 s/question (16-parallel); ~0.5 s for a 6-headline ranking (live demo) |
| 2 | `autotrust/JEV-35B` | JEV | 713,162 | 36.0B (Qwen3.5-35B-A3B MoE, ~3B active) | Apache-2.0 | 72 GB bf16 | 204 ms single request (1×B200); 1.26 s/question (32-parallel) |
| 3 | `autotrust/JEV-9B` | JEV | 542,549 | 9.0B (Qwen3.5-9B) | Apache-2.0 | 18.4 GB bf16 (Q4 GGUF ≈ 5.6 GB) | ~90 ms/decision (1×B200) vs 238–301 ms for hosted Jev; ~165 ms robot-decision; ~0.2 s/click GUI |
| 4 | `autotrust/JEV-27B` | JEV | 320,585 | 26.9B (Qwen3.8-27B text) | Apache-2.0 | 54.7 GB bf16 | 137 ms/decision (1×B200); 4.2 ms batched (128/batch, vLLM); ~130 dec/s |
| 5 | `autotrust/JEV-35B-NVFP4` | JEV (NVFP4 build) | 184,370 | 36.0B, NVFP4-quantised | Apache-2.0 | 26.7 GB (one 32–48 GB GPU) | 215 ms text / 378 ms image (1×B200) |
| 6 | `alibiserikbay/JevK5` | JevK5 | 92,289 | 4.2B (Qwen3.5-4B) | Apache-2.0 | 8.4 GB bf16 | ~13 ms/decision (H100, CUDA graphs; p50 13.2 ms; 30–162 ms on 1–4K docs) |
| 7 | `JackKozmo29/depguard-jev-style-1.5b` | Jev-style guard | 66,682 | 1.5B (Qwen2.5-1.5B-Instruct) | Apache-2.0 | 6.2 GB (fp32 build) | ~82 ms local (MPS) vs 115–125 ms (Jev API / network) |
| 8 | `JackKozmo29/mailguard-jev-style-1.5b` | Jev-style guard | 66,540 | 1.5B | Apache-2.0 | 6.2 GB (fp32 build) | ~80 ms (M2 16 GB: 78/112/134 ms) vs Jev 118/201/380 ms |
| 9 | `JackKozmo29/sevclassifier-jev-style-1.5b` | Jev-style guard | 65,293 | 1.5B | Apache-2.0 | 6.2 GB (fp32 build) | ~76 ms (M2: 76/108/129 ms) vs Jev 115/198/372 ms |
| 10 | `JackKozmo29/codeguard-jev-style-1.5b` | Jev-style guard | 65,227 | 1.5B | Apache-2.0 | 6.2 GB (fp32 build) | ~85 ms local (MPS) |
| 11 | `autotrust/JEV-Gemma4-26B-A4B` | JEV (Gemma base) | 35,975 | 25.8B (Gemma-4-26B-A4B MoE, ~4B active) | Apache-2.0 (adapter/head); **Gemma-4 terms for the base** | 51.8 GB bf16 | not published (MoE, ≈4B active/token) |
| 12 | `autotrust/AutoTrust-JEV-27B-v1.1` | JEV | 27,292 | 27.4B | Apache-2.0 | 54.7 GB bf16 | median 64.8 ms / p95 800.5 ms per request |
| 13 | `alibiserikbay/JevK5-GGUF` | JevK5 (quants) | 22,893 | 2B / 4B / 9B v0.3 builds | Apache-2.0 | Q8: ≈2.6 / 4.5 / 9.5 GB per size | ~13 ms GPU (CUDA graphs); ~0.6 s short / 1.8 s hard on CPU |
| 14 | `prithivMLmods/JEV-27B-VL-GGUF` | JEV (quants) | 17,398 | 27.5B | Apache-2.0 | Q4 16.5 GB / Q5 19.2 GB / BF16 53.8 GB (+0.9 GB mmproj) | not published (≈80–100 ms Q8 on RTX PRO 6000 class, est.) |
| 15 | `Atlas3D/JEV-27B-VL-GGUF` | JEV (quants) | 16,648 | 27.5B | Apache-2.0 | Q4 16.5 GB / Q8 28.6 GB / BF16 53.8 GB | ~80 ms/decision (Q8, RTX PRO 6000, no prompt cache) |
| 16 | `chaoliangUNSW/Jev-Style-Qwen3.5-2B-Decision-GGUF` | Jev-Style | 15,237 | 1.88B (Qwen3.5-2B-Base) | Apache-2.0 | Q4 1.3 GB / Q8 2.1 GB / BF16 3.9 GB | 77 ms/decision (M1 Max); ~110 ms over HTTP (LM Studio) |
| 17 | `iapp/OpenThai-SystemOne` | OpenThai (iApp) | 8,836 | 0.75B (Qwen3.5-0.8B-Base) | Apache-2.0 | 1.5 GB bf16 | ~40 ms/decision (H100, ~24 dec/s); 170–220 ms incl. network from a laptop |
| 18 | `prithivMLmods/JEV-9B-GGUF` | JEV (quants) | 8,247 | 9.0B | Apache-2.0 | Q4 5.6 GB / Q5 6.5 GB / Q6 7.4 GB / BF16 17.9 GB | not published (≈100–150 ms on a 24 GB GPU, est. from JEV-9B) |
| 19 | `chaoliangUNSW/Jev-Style-0.8B-Decision-v3-GGUF` | Jev-Style | 8,107 | 0.75B (Qwen3.5-0.8B) | Apache-2.0 | Q4 0.53 GB / Q8 0.81 GB / F16 1.5 GB | ~1.4 s for 10 questions sharing a 4K-token state (batched); 2.3–2.6 s for an 8K state; 25.6K-token context |
| 20 | `chaoliangUNSW/Jev-Style-Qwen3.5-2B-Decision-MLX-bf16` | Jev-Style | 7,187 | 1.88B | Apache-2.0 | 3.76 GB (MLX bf16) | 77 ms/decision (M1 Max, MLX) |

**Family notes**
- **JEV (AutoTrust)** — the most-downloaded System One family. "One decision model
  instead of a ranking team": a frozen open backbone (Qwen3.5/3.8 or Gemma-4, MoE
  where noted) plus a LoRA "Blocks of Experts" System 1 block (decision head
  initialised from `lm_head` rows, trained on Jev 1.13 distributions) and the
  unmodified backbone as System 2, routed per request. Serves TypeSafe's
  `POST /v1/systemone`-style contract; all Apache-2.0 except the Gemma-based build,
  whose base weights remain under Gemma-4 terms.
- **JevK5** — single-file Jev-style model on Qwen3.5-4B, CUDA-graph serving; #2 of 76
  on JevBench v1.4 (62.04 vs Jev 63.29); ~13 ms/decision on H100.
- **Jev-style guards (JackKozmo29)** — four 1.5B Qwen2.5 specialists (dependency,
  mail, severity, code guards) that beat the hosted Jev API on latency locally.
- **Jev-Style (chaoliangUNSW)** — 2B/0.8B decision models, GGUF + MLX builds, zero-cost
  calibration folded into the final RMSNorm; 77 ms per decision on an M1 Max; v3
  handles 25.6K-token states across 51 languages.
- **OpenThai (iApp)** — Thai+English, 0.8B, TypeSafe-compatible `/v1/systemone` API,
  256-way slot head; plays Doom at ~24 decisions/s on one H100.

## 4. Just outside the top 20 (worth knowing)

- `Contrastive-LM/CLM-v0.1-8B` (5,149 dl, Apache-2.0) — a *new class*: projection heads
  on frozen Qwen3-8B, contrastive InfoNCE; up to 9× lower latency than Jev; SOTA
  verifier (DeepSWE 81.6%, Terminal-Bench 2.1 87.6%).
- `Futurix-AI/FxAI-decision-model` (5,550 dl, Apache-2.0, 26B); `chenz53/Jev-alpha-26B-A4B`
  (6,903 dl, Apache-2.0); `akhilaaa3/Jev-Omni` (5,671 dl, Apache-2.0, 12B Gemma-4 base);
  `com-kotobalabs/open-jev-deberta-v3-large` (2,219 dl — independent DeBERTa
  reproduction, 28 ms for 10 questions on H100); `LIQIIIII/Jeva-4B` (1,714 dl — NUS,
  decision-native: null-aware, permutation-invariant, option-scalable, cacheable;
  arXiv 2610.18773); `lostargon/Tiny-Jev` (1,037); `dwidlee/systemone-lite-0.5b`
  (980, p50 13.1 ms); `convaiinnovations/laya-typed-decisions` (3,553).
- **Excluded for licensing** (open weights, not OSI open source): the whole
  **StartLux-Decision** family (11 builds, 5.7K–30.4K dl, **CC-BY-NC-4.0**),
  `WhaletechAI/W1-JEV` (4,260 dl, no license), `jinghao1632/bit-jev-2b-distilled`
  (2,764 dl, no license), `doofz/THX-01` (862 dl, no license on HF),
  `argos1111/modernbert-ja-310m-jev` (828 dl, CC-BY-SA), `pngwn/system-one-qwen3.5-4b-scorer`
  (370 dl, CC-BY-NC).
- Also notable at ~0 downloads: `mpuig/system-one-*`, `lafalce/system-one-model`,
  `hotchpotch/bekko-system-one-v0-{17m,68m,400m}` (the S1MB author's own models).

## 5. Mechanics & hardware rules of thumb

- These models answer in **one forward pass** — response time is a *prefill* cost, so
  it scales with state length, not answer length. A 0.5–1B model: 10–50 ms on a modern
  GPU / M-series laptop. 4–9B: ~13–90 ms on H100/B200. 26–36B (MoE where noted):
  ~80–400 ms on a top-end GPU.
- RAM ≈ params × bytes/weight (bf16 = 2, Q8 ≈ 1, Q4 ≈ 0.5) + ~15% overhead for
  context/cache. Adapter/head-only repos (CLM, mini-Jev) add their head size to the
  backbone's requirement.
- State caching is the big multiplier: Jev-Style v3 answers a *further* question on an
  already-computed 24.4K-token state in 0.17 s vs 16.2 s cold; CLM reuses action
  embeddings (13× faster than Jev at ~1k candidates).

## 6. Challenges

- **Calibration & generalization remain the moat.** Small open models "fall far behind
  Jev 1.13 on S1MB" (bekko's own words); JevK5, the best open model on JevBench, is
  still ~1.3 points behind; hard tiers (adversarial, long documents) are where open
  models bleed accuracy.
- **Benchmark credibility** is contested — the University of Bonn evaluation and the
  "glorified zero-shot classifier" critique question whether the category is new or a
  rebranded calibrated classifier. S1MB (100+ models, one harness) is the emerging
  neutral ground.
- **License fragmentation**: the most-downloaded non-JEV family (StartLux) is
  CC-BY-NC; several popular repos ship no license; Gemma-based builds carry mixed
  terms even when their front-matter says Apache-2.0.
- **Long states are still expensive**: 24K-token decisions cost seconds even at 2B;
  the category's "fast" claim holds best at ≤4K tokens and with state reuse.

## 7. Real-world applications

Ticket routing and severity triage; moderation; intent detection (CLINC150/MASSIVE
zero-shot); RAG relevance judging; verifying/guard-raising another model's output;
tool- and action-selection inside agents (BFCL 96.5% on mini-Jev's finite-choice
adaptation); computer-use / GUI agents (JEV-9B: 95% of 60 multi-step desktop tasks);
recommendation and re-ranking (AutoTrust GuruSearch live demo — every ranking is a
calibrated System 1 decision in ~0.5 s); embodied reasoning (JEV-27B-VL: ERQA 61.5%).

## 8. Future outlook

MoE backbones (26B-A4B, 35B-A3B) make frontier-class decision fidelity affordable on a
single 32–48 GB GPU at NVFP4; the Jev-compatible `/v1/systemone` wire contract is
becoming a de-facto standard (Ollama 0.35 ships System One models; Ollaya runtime).
Expect the open gap to close on standard benchmarks within a year, with the durable
open differentiators being: on-prem data control, per-domain fine-tuning (guards,
churn, domain NLI), and sub-10 ms tiny models (von/THX-01 class) for in-loop decisions.

## References

1. TypeSafe AI — *Introducing System One Models & Jev* (blog, Sep 15 2026)
2. TypeSafe AI — product page ("not chat")
3. InfoQ — *TypeSafe AI Releases Jev: a Decision-Only Model That Returns Typed Probabilities Instead of Text* (Oct 1 2026)
4. Victor Dibia — *How Jev works: calibrated decision models* (victordibia.com)
5. Minh Le Duc — *What Is RLCD, and Why It Makes Jev Fast Instead of Smart* (gopenai, Sep 25 2026)
6. Yuichi Tateno (hotchpotch) — *S1MB: comparing System One Decision Models across 100+ benchmarks* (Sep 30 2026)
7. Deußer, Sparrenberg et al. (Univ. of Bonn / Lamarr) — *Evaluating and Benchmarking the System One Model Jev*
8. Qi Li, Wang et al. (NUS) — *Jeva: System One Models from First Principles* (arXiv:2610.18773)
9. Contrastive-LM — *CLM-v0.1-8B* card + MarkTechPost coverage (Sep 23 2026)
10. cobanov — *awesome-jev* (curated, source-backed list, 297 commits)
11. chенrongwei (r/LLMDevs) — *I reviewed 287 open-source Jev projects*
12. wfzyx — *von: open-source 395M non-autoregressive System One model* (GitHub + HF)
13. doofz (HAL-X AI) — *THX-01: 322M decision model for your phone* (HF blog, Oct 10 2026)
14. Oumi — *How to Build a Decision Model Like Jev*
15. Superglue — *Jev: new model category or glorified classifier* (S1MB benchmark write-up)
16. HuggingFace model cards (live API, Oct 23 2026) for all 20 listed models and the near-miss repos
