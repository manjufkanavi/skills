# Qwen3.6-35B-A3B MLX Fine-Tunes — Complete Catalog

**Date:** 2026-08-15
**Base model:** Qwen3.6-35B-A3B (sparse MoE, 35B total / ~3B active, Apache 2.0, 262K native context)
**Format:** MLX (for Mac Studio / Apple Silicon via omlx)

---

## Executive Summary

The Qwen3.6-35B-A3B ecosystem has exploded with fine-tunes. Beyond the base model quants, there are **four major fine-tune families** built on this architecture, each with MLX conversions:

1. **Qwen3.6-35B-A3B direct fine-tunes** — reasoning-distilled, abliterated/uncensored, and specialized variants
2. **KAT-Coder-V2.5-Dev** — the top coding fine-tune (70.6% SWE-Bench Verified)
3. **Agents-A1** — agentic/tool-use fine-tune from InternScience
4. **Ornith-1.0-35B** — the most popular general-purpose fine-tune (3.1M+ downloads)

---

## 1. Top MLX Fine-Tunes by Downloads

### Reasoning-Distilled (Claude Opus)

| Model | Downloads | Notes |
|-------|-----------|-------|
| `mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit` | 6,989 | Opus 4.7 reasoning + abliterated, 8-bit |
| `stamsam/Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-MLX-oQ4-MTP` | 3,420 | Opus 4.7 reasoning distilled, oQ4 + MTP |
| `splats/Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-oQ4e` | 288 | oQ4e variant |
| `nabi-chan/Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-MLX-4bit` | 320 | 4-bit abliterated |
| `vanch007/Huihui-Qwen3.6-35B-A3B-abliterated-mlx-4bit` | 347 | Huihui abliterated 4-bit |
| `IHateCrickets/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-MLX-6bit` | 593 | 6-bit variant |
| `m5max/Huihui-Qwen3.6-35B-A3B-Claude-4.6-Opus-abliterated-mlx-oQ8-mtp` | 435 | 4.6 Opus + MTP |

### Uncensored / Abliterated

| Model | Downloads | Notes |
|-------|-----------|-------|
| `froggeric/Qwen3.6-35B-A3B-Uncensored-Heretic-MLX-4bit` | 10,071 | **Most downloaded fine-tune** — Heretic uncensored |
| `Youssofal/Qwen3.6-35B-A3B-Abliterated-Heretic-MLX-4bit` | 2,356 | Abliterated + Heretic |
| `froggeric/Qwen3.6-35B-A3B-Uncensored-Heretic-MLX-8bit` | 2,288 | 8-bit variant |
| `dawncr0w/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-text-oQ4` | 1,359 | HauhauCS aggressive uncensored |
| `Youssofal/Qwen3.6-35B-A3B-Abliterated-Heretic-MLX-8bit` | 815 | 8-bit |
| `froggeric/Qwen3.6-35B-A3B-Uncensored-Heretic-MLX-6bit` | 807 | 6-bit |
| `symrex/Qwen3.6-35B-A3B-Uncensored-Genesis-Hermes-V7-dequantized-oQ8e-mtp` | 979 | Hermes V7 uncensored + MTP |

### Specialized / Agentic

| Model | Downloads | Notes |
|-------|-----------|-------|
| `deadbydawn101/RavenX-CyberAgent-Qwen3.6-35B-A3B-Opus-4.7-OpenMythos-Pentester-BugHunter-RATH-mlx` | 3,620 | Cyber/pentest agent |
| `EschaLabs/Qwen3.6-35B-A3B-Escha-W2` | 6,663 | Escha W2 — 253 likes, highest-liked fine-tune |
| `peculiar-ragdoll/Nail-Qwen3.6-35B-A3B-MLX` | 1,644 | Nail fine-tune |
| `z-lab/Qwen3.6-35B-A3B-PARO` | 1,395 | PARO fine-tune |
| `samuelfaj/Qwen3.6-35B-A3B-NSC-ACE-SABER-6bit-MTPLX-Optimized-Speed` | 789 | NSC ACE SABER, speed-optimized |
| `thetom-ai/Qwen3.6-35B-A3B-ConfigI-MLX` | 228 | ConfigI |

---

## 2. KAT-Coder-V2.5-Dev (Coding Fine-Tune)

Base: Qwen3.6-35B-A3B. **70.6% SWE-Bench Verified** — top local coding model.

### MLX Variants

| Model | Downloads | Notes |
|-------|-----------|-------|
| `mlx-community/KAT-Coder-V2.5-Dev-OptiQ-4bit` | 4,998 | **Best MLX option** — OptiQ 4-bit |
| `leonsarmiento/KAT-Coder-V2.5-Dev-6bit-XL-mlx` | 1,923 | 6-bit XL |
| `ZQ-Dev/KAT-Coder-V2.5-Dev-oQ8e` | 1,224 | oQ8e |
| `ZQ-Dev/KAT-Coder-V2.5-Dev-oQ6e` | 520 | oQ6e |
| `ZQ-Dev/KAT-Coder-V2.5-Dev-oQ5e` | 289 | oQ5e |
| `ZQ-Dev/KAT-Coder-V2.5-Dev-oQ4e` | 560 | oQ4e |
| `ZQ-Dev/KAT-Coder-V2.5-Dev-oQ3e` | 332 | oQ3e |
| `ZQ-Dev/KAT-Coder-V2.5-Dev-oQ2e` | 599 | oQ2e |
| `mlx-works/KAT-Coder-V2.5-Dev-oQ4e-mtp` | 461 | oQ4e + MTP |
| `mlx-works/KAT-Coder-V2.5-Dev-oQ2e-mtp` | 359 | oQ2e + MTP |
| `jason-schulz/KAT-Coder-V2.5-Dev-VL-oQ8e-mtp` | 506 | Vision-language + MTP |
| `jason-schulz/KAT-Coder-V2.5-Dev-VL-oQ4e-mtp` | 435 | VL oQ4e + MTP |
| `jason-schulz/KAT-Coder-V2.5-Dev-VL-oQ6e-mtp` | 328 | VL oQ6e + MTP |
| `majentik/KAT-Coder-V2.5-Dev-MLX-4bit` | 79 | 4-bit |
| `majentik/KAT-Coder-V2.5-Dev-MLX-6bit` | 187 | 6-bit |
| `majentik/KAT-Coder-V2.5-Dev-MLX-8bit` | 105 | 8-bit |
| `majentik/KAT-Coder-V2.5-Dev-MLX-MXFP4` | 258 | MXFP4 |
| `sluttybutfast/KAT-Coder-V2.5-Dev-Vision-OptiQ-4bit` | 448 | Vision variant |
| `npario/KAT-Coder-V2.5-Dev-Vision-OptiQ-4bit` | 139 | Vision variant |
| `jedisct1/KAT-Coder-V2.5-Dev-oQ8e` | 212 | oQ8e |
| `jedisct1/KAT-Coder-V2.5-Dev-oQ4e` | 292 | oQ4e |

---

## 3. Agents-A1 (Agentic Fine-Tune)

Base: Qwen3.6-35B-A3B. From InternScience — optimized for agent/tool-use workflows.

### MLX Variants

| Model | Downloads | Notes |
|-------|-----------|-------|
| `mlx-community/Agents-A1-4bit` | 1,515 | **Best MLX option** — 4-bit |
| `wang-yang/Agents-A1-MTPLX-Q4` | 1,445 | MTPLX Q4 |
| `mlx-community/Agents-A1-OptiQ-4bit` | 915 | OptiQ 4-bit |
| `mlx-community/Agents-A1-8bit` | 888 | 8-bit |
| `mlx-community/Agents-A1-6bit` | 372 | 6-bit |
| `mlx-community/Agents-A1-5bit` | 295 | 5-bit |
| `mlx-community/Agents-A1-bf16` | 474 | bf16 |
| `mlx-community/Agents-A1-3bit` | 115 | 3-bit |
| `felkf/Ornith-Agents-A1-3.7-35B-A3B-dare_ties_v4-oQ6-fp16` | 2,640 | **Ornith merge** — dare_ties v4 |
| `felkf/Agents-A1-oQ6-fp16` | 86 | oQ6 fp16 |
| `felkf/Agents-A1-oQ8-fp16` | 156 | oQ8 fp16 |
| `leonsarmiento/Agents-A1-6bit-XL-mlx` | 232 | 6-bit XL |
| `leonsarmiento/Ornith-Agents-A1-3.6-35B-A3B-dare_ties-6bit-XL-mlx` | 527 | Ornith dare_ties 6-bit |
| `leonsarmiento/Ornith-Agents-A1-3.6-35B-A3B-task_arithmetic_v2-6bit-XL-mlx` | 764 | Ornith task_arithmetic v2 |
| `DreamFoundries/Agents-A1-4bit` | 237 | 4-bit |
| `DreamFoundries/Agents-A1-6bit` | 88 | 6-bit |
| `DreamFoundries/Agents-A1-8bit` | 102 | 8-bit |
| `Basher17/Agents-A1-oQ6e` | 191 | oQ6e |
| `Basher17/Agents-A1-oQ4e` | 188 | oQ4e |
| `swdjojo/Agents-A1-oQ4e` | 20 | oQ4e |
| `swdjojo/Agents-A1-oQ5e` | 12 | oQ5e |
| `swdjojo/Agents-A1-oQ6e` | 18 | oQ6e |
| `swdjojo/Agents-A1-oQ8e` | 49 | oQ8e |
| `swdjojo/Huihui-Agents-A1-abliterated-oQ4e` | 18 | Abliterated oQ4e |
| `swdjojo/Huihui-Agents-A1-abliterated-oQ8e` | 49 | Abliterated oQ8e |
| `m-i/Agents-A1-mlx-mixed-mxfp4-bf16` | 110 | Mixed MXFP4/BF16 |
| `mlx-works/Agents-A1-oQ2` | 254 | oQ2 |
| `georgeis55/Agents-A1-mlx-oQ8` | 143 | oQ8 |
| `Brooooooklyn/Agents-A1-mxfp4-mlx` | 73 | MXFP4 |
| `Brooooooklyn/Agents-A1-nvfp4-mlx` | 94 | NVFP4 |
| `Elsephire/Qwen3.6-35B-A3B-Agents-A1-80-20-Beta` | 5 | 80/20 blend |

### Agents-A1-4B (smaller variant, also MLX)

| Model | Downloads | Notes |
|-------|-----------|-------|
| `wcamon/Agents-A1-4B-MLX-4bit` | 804 | 4-bit |
| `yugeshkarunamurthy/Agents-A1-4B-oQe6` | 657 | oQe6 |
| `yugeshkarunamurthy/Agents-A1-4B-oQe4` | 423 | oQe4 |
| `ToPo-ToPo/Agents-A1-4B-mlx-4bit` | 152 | 4-bit |
| `ToPo-ToPo/Agents-A1-4B-mlx-8bit` | 243 | 8-bit |
| `ToPo-ToPo/Agents-A1-4B-mlx-bf16` | 161 | bf16 |
| `thoddnn/Agents-A1-4B-MLX-4bit` | 218 | 4-bit |
| `opnir/Agents-A1-4B-oQ8e-fp16` | 105 | oQ8e fp16 |
| `brainworkup/Agents-A1-4B-oQ8e` | 56 | oQ8e |
| `djrsystemservices/Agents-A1-4B-oQ8e-mtp` | 4 | oQ8e + MTP |
| `djrsystemservices/Agents-A1-4B-oQ6e-mtp` | 5 | oQ6e + MTP |
| `Brooooooklyn/Agents-A1-4B-mxfp4-mlx` | 121 | MXFP4 |
| `Brooooooklyn/Agents-A1-4B-nvfp4-mlx` | 78 | NVFP4 |

---

## 4. Ornith-1.0-35B (Most Popular Fine-Tune)

Base: Qwen3.6-35B-A3B. **3.1M+ downloads** on the base model — the most successful fine-tune of this architecture.

### MLX Variants

| Model | Downloads | Notes |
|-------|-----------|-------|
| `wang-yang/Ornith-1.0-35B-MTPLX` | 9,750 | **Best MLX option** — MTPLX |
| `mlx-community/Ornith-1.0-35B-4bit` | 4,723 | 4-bit |
| `mlx-community/Ornith-1.0-35B-8bit` | 2,854 | 8-bit |
| `mlx-community/Ornith-1.0-35B-6bit` | 1,771 | 6-bit |
| `mlx-community/Ornith-1.0-35B-bf16` | 1,708 | bf16 |
| `mlx-community/Ornith-1.0-35B-5bit` | 360 | 5-bit |
| `mlx-community/Ornith-1.0-35B-OptiQ-4bit` | 1,523 | OptiQ 4-bit |
| `mlx-community/Ornith-1.0-35B-OptiQ-6bit` | 261 | OptiQ 6-bit |
| `lmstudio-community/Ornith-1.0-35B-MLX-8bit` | 2,396 | 8-bit |
| `lmstudio-community/Ornith-1.0-35B-MLX-4bit` | 1,666 | 4-bit |
| `lmstudio-community/Ornith-1.0-35B-MLX-6bit` | 911 | 6-bit |
| `lmstudio-community/Ornith-1.0-35B-MLX-5bit` | 596 | 5-bit |
| `leonsarmiento/Ornith-1.0-35B-5bit-XL-mlx` | 2,405 | 5-bit XL |
| `leonsarmiento/Ornith-1.0-35B-5bit-mlx` | 1,324 | 5-bit |
| `leonsarmiento/Ornith-1.0-35B-oQ4e-XL-mlx` | 347 | oQ4e XL |
| `leonsarmiento/Ornith-1.0-35B-uncensored-heretic-5bit-XL-mlx` | 1,866 | Heretic uncensored 5-bit XL |
| `georgeis55/Ornith-1.0-35B-MLX-oQ8-mtp` | 1,050 | oQ8 + MTP |
| `georgeis55/Ornith-1.0-35B-MLX-oQ8` | 335 | oQ8 |
| `georgeis55/Ornith-1.0-35B-MLX-oQ8-fp16` | 90 | oQ8 fp16 |
| `georgeis55/Ornith-1.0-35B-MLX-oQ4` | 145 | oQ4 |
| `Jonandrop/Ornith-1.0-35B-MTPLX-Vision` | 806 | Vision + MTPLX |
| `Jonandrop/Ornith-1.0-35B-MTPLX-Vision-mxfp4-int4-mtp` | 905 | Vision MXFP4 + MTP |
| `swdjojo/Ornith-1.0-35B-AEON-Ultimate-Uncensored-oQ8e` | 806 | AEON Ultimate uncensored |
| `swdjojo/Ornith-1.0-35B-AEON-Ultimate-Uncensored-oQ6e` | 483 | AEON 6-bit |
| `swdjojo/Ornith-1.0-35B-oQ6e` | 161 | oQ6e |
| `deepsweet/Ornith-1.0-35B-MLX-oQ8` | 339 | oQ8 |
| `deepsweet/Ornith-1.0-35B-MLX-oQ4` | 284 | oQ4 |
| `deepsweet/Ornith-1.0-35B-MLX-VL-oQ4-FP16` | 271 | VL oQ4 fp16 |
| `deepsweet/Ornith-1.0-35B-MLX-VL-oQ8-FP16` | 275 | VL oQ8 fp16 |
| `deepsweet/Ornith-1.0-35B-MLX-oQ4-FP16` | 80 | oQ4 fp16 |
| `Shiftedx/ornith-1.0-35b-mxfp4-vision-mtplx` | 513 | Vision MXFP4 + MTPLX |
| `Shiftedx/ornith-1.0-35b-mxfp4-mlx` | 225 | MXFP4 |
| `Shiftedx/ornith-1.0-35b-mxfp8-mlx` | 258 | MXFP8 |
| `Shiftedx/ornith-1.0-35b-abliterated-mxfp4-mtplx` | 264 | Abliterated MXFP4 |
| `OsaurusAI/Ornith-1.0-35B-MXFP8` | 593 | MXFP8 |
| `OsaurusAI/Ornith-1.0-35B-MXFP4` | 498 | MXFP4 |
| `OsaurusAI/Ornith-1.0-35B-JANG_4M` | 259 | JANG 4M |
| `JANGQ-AI/Ornith-1.0-35B-JANG_6M` | 243 | JANG 6M |
| `ilyakam/Geer-Ornith-1.0-35B-A3B-6bit-MLX` | 451 | Geer 6-bit |
| `ilyakam/Geer-Ornith-1.0-35B-A3B-4-8bit-MLX` | 336 | Geer 4/8-bit |
| `Jedaye/Ornith-1.0-35B-heretic-mlx-8bit` | 2,049 | Heretic 8-bit |
| `ailexleon/Ornith-1.0-35B-uncensored-heretic-mlx-8Bit` | 1,144 | Heretic uncensored 8-bit |
| `Justanut/Ornith-1.0-35B-uncensored-heretic-oQ6e` | 605 | Heretic oQ6e |
| `mlx-works/Ornith-1.0-35B-oQ2` | 738 | oQ2 |
| `ToPo-ToPo/Ornith-1.0-35B-mlx-4bit` | 209 | 4-bit |
| `ToPo-ToPo/Ornith-1.0-35B-mlx-8bit` | 68 | 8-bit |
| `ToPo-ToPo/Ornith-1.0-35B-mlx-bf16` | 82 | bf16 |
| `majentik/Ornith-1.0-35B-MLX-2bit` | 286 | 2-bit |
| `maxlaurence/Ornith-1.0-35B-oQ5` | 252 | oQ5 |
| `idangazit/Ornith-1.0-35B-oQ4` | 351 | oQ4 |
| `nathansutton/Ornith-1.0-35B-Q6-MLX` | 192 | Q6 |
| `nathansutton/Ornith-1.0-35B-UD-Q2_K_XL-MLX` | 338 | UD Q2_K_XL |
| `datls/Ornith-1.0-35B-oQ8e` | 93 | oQ8e |
| `zviratko/Ornith-1.0-35B-oQ8e` | 178 | oQ8e |
| `mlx-coders/Ornith-1.0-35B-oQ8e` | 215 | oQ8e |
| `a-gordo/Ornith-1.0-35B-MLX-oQ8-fp16` | 132 | oQ8 fp16 |
| `npario/Ornith-1.0-35B-5bit-XL-mlx` | 52 | 5-bit XL |
| `npario/Ornith-1.0-35B-OptiQ-4bit` | 114 | OptiQ 4-bit |
| `AutomatosX/AX-Ornith-1.0-35B-MLX-AXQ-6bit` | 152 | AXQ 6-bit |
| `AutomatosX/AX-Ornith-1.0-35B-MLX-AXQ-4bit` | 26 | AXQ 4-bit |
| `wd01216-bit/Ornith-1.0-35B-MLX-3bit-MTP` | 392 | 3-bit + MTP |
| `zwcf5200/Ornith-1.0-35B-Vision` | 214 | Vision |
| `Joseph007fu/Ornith-1.0-35B-MTP2-MTPLX` | 0 | MTP2 |
| `blackfan23/Ornith-1.0-35B-Qwen3.6MTP-oQ4` | 217 | Qwen3.6 MTP oQ4 |
| `programmer-666/Ornith-1.0-35B-oQ8e` | 216 | oQ8e |
| `NapYang/Ornith-1.0-35B-MLX-oQ3.5-fp16` | 220 | oQ3.5 fp16 |
| `abshake96/Ornith-1.0-35B-mlx-4bit` | 0 | 4-bit |
| `PocketAiHub/Ornith-1.0-35B-MLX` | 0 | Generic MLX |
| `Brooooooklyn/Ornith-1.0-35B-mxfp4-mlx` | 293 | MXFP4 |
| `Brooooooklyn/Ornith-1.0-35B-nvfp4-mlx` | 316 | NVFP4 |

---

## 5. Cross-Family Merges (Ornith × Agents-A1)

| Model | Downloads | Notes |
|-------|-----------|-------|
| `felkf/Ornith-Agents-A1-3.7-35B-A3B-dare_ties_v4-oQ6-fp16` | 2,640 | **Best merge** — dare_ties v4 |
| `leonsarmiento/Ornith-Agents-A1-3.6-35B-A3B-task_arithmetic_v2-6bit-XL-mlx` | 764 | task_arithmetic v2 |
| `leonsarmiento/Ornith-Agents-A1-3.6-35B-A3B-dare_ties-6bit-XL-mlx` | 527 | dare_ties 6-bit |
| `nightmedia/Qwen3.6-35B-A3B-Fable-Holo3.1-Qwopus-KAT-Coder-C-qx86-hi-mlx` | 2,497 | **Fable + Holo3.1 + Qwopus + KAT-Coder** mega-merge |

---

## 6. Recommendations for Your Mac Studio

### Best Overall (General Purpose)
- **`wang-yang/Ornith-1.0-35B-MTPLX`** — 9,750 downloads, MTPLX format, best balance of quality and speed
- **`mlx-community/Ornith-1.0-35B-4bit`** — 4,723 downloads, standard 4-bit

### Best for Coding
- **`mlx-community/KAT-Coder-V2.5-Dev-OptiQ-4bit`** — 4,998 downloads, OptiQ 4-bit, 70.6% SWE-Bench
- **`leonsarmiento/KAT-Coder-V2.5-Dev-6bit-XL-mlx`** — 6-bit XL for higher quality

### Best for Agentic/Tool-Use
- **`mlx-community/Agents-A1-4bit`** — 1,515 downloads, standard 4-bit
- **`wang-yang/Agents-A1-MTPLX-Q4`** — 1,445 downloads, MTPLX

### Best Uncensored
- **`froggeric/Qwen3.6-35B-A3B-Uncensored-Heretic-MLX-4bit`** — 10,071 downloads, most popular fine-tune overall

### Best Reasoning (Claude Opus Distilled)
- **`mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit`** — 6,989 downloads
- **`stamsam/Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-MLX-oQ4-MTP`** — 3,420 downloads, includes MTP

### Best Mega-Merge
- **`nightmedia/Qwen3.6-35B-A3B-Fable-Holo3.1-Qwopus-KAT-Coder-C-qx86-hi-mlx`** — combines Fable, Holo3.1, Qwopus, and KAT-Coder

---

## Key Insights

1. **Ornith-1.0-35B dominates** — 3.1M+ downloads on the base, with the most extensive MLX ecosystem
2. **KAT-Coder is the coding king** — 70.6% SWE-Bench Verified, beats gpt-oss-120B
3. **MTP variants are emerging** — several fine-tunes now ship with MTP support baked in (stamsam, mlx-works, jason-schulz, wd01216-bit)
4. **Vision variants exist** — KAT-Coder-VL, Ornith-Vision, Shiftedx vision variants for multimodal use
5. **Merges are the frontier** — dare_ties and task_arithmetic merges combine Ornith + Agents-A1 strengths
6. **Quantization diversity** — oQ4e/oQ6e/oQ8e (OptiQ), MXFP4, NVFP4, JANG, TurboQuant, RotorQuant all available in MLX
