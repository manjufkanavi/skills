# MLX Local Model Demo — Vanilla vs RAG Side-by-Side

How to demo a local MLX model comparing a *vanilla* (retrieval-blind) run against a *RAG*
(retrieval-augmented) run, side by side, sharing one backend. Written for the Solvarch project
(Qwen2.5-Coder-3B-Instruct-8bit) but the pattern is generic.

## Core idea: one model, two prompt modes

Vanilla and RAG are the **same model** — the only difference is whether retrieved context is
injected into the prompt. So "wiring them to the same backend" is deliberately trivial:

```
user query ──► /generate?mode=vanilla|rag&query=…
                  ├─ mode=vanilla  → prompt WITHOUT context
                  └─ mode=rag      → prompt WITH retrieved chunks
                          │
                  [ single MLX model, loaded once ]
                          │
                 side-by-side output
```

One model instance, one `/generate` endpoint, a `mode` flag. Vanilla = instruction-only prompt;
RAG = instruction + retrieved context. **Retrieval is the only thing that differs.**

## Stack (minimal, proven)

- **Runtime:** MLX `0.31.2` (system `python3` / homebrew python3).
- **Harness:** `mlx_lm` (NOT installed by default). Create a dedicated venv:
  ```bash
  uv venv ~/.venvs/solvarch-demo --python 3.11
  # install into it — uv venvs ship no pip:
  VIRTUAL_ENV=~/.venvs/solvarch-demo uv pip install "mlx==0.21.*" mlx_lm
  ```
- **Run with the venv's python binary directly** (an env var alone does not redirect `python3`):
  ```bash
  ~/.venvs/solvarch-demo/bin/python your_script.py
  ```
- **Backend:** one FastAPI/Flask app exposing `/generate`.
- **UI:** a single HTML page, two columns — **Vanilla** | **RAG** — that POSTs the *same* query to
  both and shows (a) both answers, (b) the exact prompt each received, (c) retrieved sources for RAG.

Do NOT demo in the raw `mlx_lm.chat` CLI: single-stream, no side-by-side, and hard to script two
parallel identical-condition runs (a fair demo needs both runs under identical settings).

## Loading the model — HF cache gotcha (READ THIS FIRST)

The Qwen2.5-Coder-3B-Instruct-8bit MLX model lives under:
`~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-Coder-3B-Instruct-8bit/`

`load()` needs the **snapshot dir**, not the cache root:

- WRONG: `.../models--mlx-community--Qwen2.5-Coder-3B-Instruct-8bit` (cache root) →
  `FileNotFoundError: No safetensors found`.
- RIGHT: `.../snapshots/<revision>/` (the dir containing `config.json`, `tokenizer.json`,
  `model.safetensors.index.json`).

The snapshot dir holds **symlinks into `blobs/`** (`config.json`, `tokenizer.json`,
`model.safetensors.index.json`, …). The actual weight file is a separate blob.

**Incomplete-download signature:** cache total is tiny (e.g. 75 MB) while the full 8-bit 3B model
is ~1.7 GB. A blob named `*.efff72e2.incomplete` means the weights download was interrupted — no
weight file → "No safetensors found". **Fix:** complete the download (re-run the model fetch /
`huggingface-cli download`) so the weight blob lands, then `load()` works.

## Prompt templates

- **Vanilla:** system instruction + user query only (no corpus).
- **RAG:** system instruction + retrieved AWS context chunks (top-K) + user query.

Show both prompts in the UI so the difference is visible: vanilla tends to hallucinate / omit AWS
specifics; RAG cites docs and satisfies constraints.

## Retrieval (RAG path only)

Start simple (enough to prove the demo): BM25 / lexical match over a small corpus (even 10–20
sample AWS docs). Promote to the full hybrid (BM25 Whoosh + FAISS `all-MiniLM-L6-v2` + RRF k=60 +
cross-encoder) later — see the `retrieval-engineering` skill.

## References

- `llm-deployment` (umbrella) — local LLM serving backends.
- `retrieval-engineering` — hybrid retrieval pipeline (BM25 / FAISS / RRF / cross-encoder).
- `solvarch-training` — the QLoRA fine-tuned model this demo wraps.
