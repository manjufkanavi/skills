---
name: hermes-model-switcher
description: "Switch Hermes Agent model — list oMLX models, check RAM, load/unload, update config, verify."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [hermes, model, switch, mlx, omlx]
---

# Hermes Model Switcher

Switch the active Hermes Agent model by interacting with the local oMLX inference server (port 1234).

## Prerequisites

- oMLX running on `http://localhost:1234`
- `hermes` CLI available
- `curl` available (bundled with macOS)

## Script Location

All oMLX API calls go through a single wrapper:

```
~/.hermes/skills/hermes-model-switcher/scripts/omlx_api.sh
```

### API Endpoints

| Function | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| `list_models` | `/v1/models` | GET | List all available model IDs |
| `model_status` | `/v1/models/status` | GET | Models with load state, sizes, engine type |
| `health` | `/health` | GET | Current loaded model, RAM usage, ceiling |
| `load_model <id>` | `/v1/models/{id}/load` | POST | Load a model into memory |
| `unload_model <id>` | `/v1/models/{id}/unload` | POST | Unload a model from memory |

### Usage

```bash
SCRIPT="~/.hermes/skills/hermes-model-switcher/scripts/omlx_api.sh"

$SCRIPT list_models
$SCRIPT model_status
$SCRIPT health
$SCRIPT load_model "Qwen3.6-35B-A3B-UD-MLX-4bit"
$SCRIPT unload_model "Qwen3.6-35B-A3B-UD-MLX-4bit"
```

---

## Workflow

### Step 1 — Gather State

Run all three status calls to present a complete picture:

```bash
SCRIPT="~/.hermes/skills/hermes-model-switcher/scripts/omlx_api.sh"

# System memory overview
HEALTH=$($SCRIPT health)
echo "$HEALTH" | python3 -c "
import json, sys
h = json.load(sys.stdin)
ceiling = h['final_ceiling']
used = h['current_model_memory']
free = ceiling - used
loaded = h['engine_pool']['loaded_count']
total = h['engine_pool']['model_count']
current = h['default_model']
print(f'📊 System Memory')
print(f'   Ceiling:  {ceiling/1e9:.1f} GB')
print(f'   Used:     {used/1e9:.1f} GB')
print(f'   Free:     {free/1e9:.1f} GB')
print(f'   Loaded:   {loaded}/{total} models')
print(f'   Current:  {current}')
"

# Full model table
STATUS=$($SCRIPT model_status)
echo "$STATUS" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print()
print(f'📋 Available Models ({data[\"model_count\"]} total, {data[\"loaded_count\"]} loaded)')
print(f'   Ceiling: {data[\"final_ceiling\"]/1e9:.1f} GB | Used: {data[\"current_model_memory\"]/1e9:.1f} GB | Free: {(data[\"final_ceiling\"]-data[\"current_model_memory\"])/1e9:.1f} GB')
print()
for m in data['models']:
    loaded = '✅' if m['loaded'] else '❌'
    size_gb = m['estimated_size'] / 1e9 if m['estimated_size'] else 0
    print(f'   {loaded}  {m[\"id\"]:50s} {size_gb:6.2f} GB  {m[\"engine_type\"]:10s} {m[\"model_type\"]}')
"
```

### Step 2 — User Selection

Present the model list in a formatted table. Ask the user to pick a model by typing its exact ID.

```
🤖 Available Models

┌──────────────────────────────────────────────────────┬────────┬──────────┬────────────┬──────────┐
│ Model ID                                             │ Status │ Size     │ Engine     │ Type     │
├──────────────────────────────────────────────────────┼────────┼──────────┼────────────┼──────────┤
│ ✅ Kokoro-82M-bf16                                   │ Loaded │   0.37 GB│ audio_tts  │ audio_tts│
│ ❌ OBLITERATUS-Qwen3.8-27B-OBLITERATED-4bit-MLX      │  Free  │  17.82 GB│ vlm        │ vlm      │
│ ❌ Ornith-1.5-35B-A3B-MLX-4bit                       │  Free  │  20.48 GB│ batched    │ llm      │
│ ❌ Ornith-1.5-9B-MLX-4bit                            │  Free  │   5.29 GB│ batched    │ llm      │
│ ❌ Ornith-1.5-9B-uncensored-MLX-8bit                 │  Free  │  10.95 GB│ vlm        │ vlm      │
│ ❌ Qwen3-0.6B                                        │  Free  │   1.58 GB│ batched    │ llm      │
│ ❌ Qwen3.5-0.8B-MLX-4bit                             │  Free  │   0.66 GB│ vlm        │ vlm      │
│ ❌ Qwen3.5-4B-MLX-4bit                               │  Free  │   3.19 GB│ vlm        │ vlm      │
│ ❌ Qwen3.5-9B-MLX-4bit                               │  Free  │   6.25 GB│ vlm        │ vlm      │
│ ❌ Qwen3.6-35B-A3B-DFlash                            │  Free  │   0.81 GB│ batched    │ llm      │
│ ✅ Qwen3.6-35B-A3B-UD-MLX-4bit                       │ Loaded │  22.72 GB│ vlm        │ vlm      │
│ ❌ Qwen3.8-27B-MLX-4bit                              │  Free  │  16.86 GB│ vlm        │ vlm      │
│ ❌ Qwen3.8-27B-MTP-4bit                              │  Free  │   0.25 GB│ batched    │ llm      │
│ ❌ TheCluster--amoral-gemma-3-12B-v2-mlx-4bit        │  Free  │   8.43 GB│ vlm        │ vlm      │
│ ❌ mlx-community--Llama-3.2-3B-Instruct-4bit         │  Free  │   1.90 GB│ batched    │ llm      │
│ ❌ mlx-community--gemma-3-12b-it-4bit                │  Free  │   8.43 GB│ vlm        │ vlm      │
│ ❌ text_encoder                                      │  Free  │   8.45 GB│ batched    │ llm      │
│ ❌ transformer                                       │  Free  │   8.14 GB│ batched    │ llm      │
│ ❌ vae                                               │  Free  │   0.18 GB│ batched    │ llm      │
│ ✅ MarkItDown                                        │ Loaded │   0.00 GB│ markitdown │ markitdown│
└──────────────────────────────────────────────────────┴────────┴──────────┴────────────┴──────────┘

Memory: 22.7 GB / 55.7 GB used · 32.9 GB free

Which model do you want to switch to? (type the exact Model ID)
```

### Step 3 — Unload Confirmation

Show currently loaded models and ask for confirmation:

```
📦 Currently Loaded Models

┌──────────────────────────────────────────────┬──────────┐
│ Model ID                                     │ Size     │
├──────────────────────────────────────────────┼──────────┤
│ Qwen3.6-35B-A3B-UD-MLX-4bit                  │  22.72 GB│
│ MarkItDown                                   │   0.00 GB│
└──────────────────────────────────────────────┴──────────┘

⚠️  Unload existing model(s) before loading new one? (y/n)
```

### Step 4 — Unload Existing Models

If user confirms (`y`), unload each loaded model:

```bash
SCRIPT="~/.hermes/skills/hermes-model-switcher/scripts/omlx_api.sh"

# Unload each loaded model
for model_id in "Qwen3.6-35B-A3B-UD-MLX-4bit" "MarkItDown"; do
  echo "⏳ Unloading $model_id ..."
  RESULT=$($SCRIPT unload_model "$model_id")
  echo "   $RESULT"
done

# Verify all unloaded
HEALTH=$($SCRIPT health)
echo "$HEALTH" | python3 -c "
import json, sys
h = json.load(sys.stdin)
loaded = h['engine_pool']['loaded_count']
print(f'✅ Unload complete. {loaded} models still loaded.')
"
```

### Step 5 — Load New Model

```bash
SCRIPT="~/.hermes/skills/hermes-model-switcher/scripts/omlx_api.sh"
MODEL_ID="<user_selected_model>"

echo "⏳ Loading $MODEL_ID ..."
RESULT=$($SCRIPT load_model "$MODEL_ID")
echo "   $RESULT"

# Poll until loaded
echo -n "   Waiting for load to complete..."
for i in $(seq 1 30); do
  sleep 2
  STATUS=$($SCRIPT model_status)
  LOADED=$(echo "$STATUS" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for m in data['models']:
    if m['id'] == '$MODEL_ID':
        print('true' if m['loaded'] else 'false')
        break
")
  if [[ "$LOADED" == "true" ]]; then
    echo " ✅ Loaded!"
    break
  fi
  echo -n "."
done
```

### Step 6 — Switch Hermes Config

```bash
# Update Hermes to point to the new model
hermes config set model.provider custom
hermes config set model.default "$MODEL_ID"
hermes config set model.base_url "http://localhost:1234"
```

### Step 7 — Verify

```bash
SCRIPT="~/.hermes/skills/hermes-model-switcher/scripts/omlx_api.sh"

# Verify oMLX has the model loaded
HEALTH=$($SCRIPT health)
CURRENT=$(echo "$HEALTH" | python3 -c "import json,sys; print(json.load(sys.stdin)['default_model'])")

if [[ "$CURRENT" == "$MODEL_ID" ]]; then
  echo "✅ oMLX confirms: $CURRENT is loaded"
else
  echo "⚠️  oMLX default_model is '$CURRENT', expected '$MODEL_ID'"
fi

# Verify Hermes config
echo ""
echo "🔧 Hermes Config:"
hermes config | grep -E "default|provider|base_url" | head -5
```

### Step 8 — Inform User

```
🎉 Model Switch Complete

┌─────────────────────────────────────────────────────────────────┐
│  Old Model:  Qwen3.6-35B-A3B-UD-MLX-4bit                       │
│  New Model:  <MODEL_ID>                                        │
│  RAM Usage:  <new_used> GB / <ceiling> GB (<free> GB free)     │
│  Load Time:  <seconds>s                                        │
└─────────────────────────────────────────────────────────────────┘

⚡ Run /reset in this session for changes to take effect.
```

---

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `curl: connect refused` | oMLX not running | Start oMLX server |
| `model not found` | Invalid model ID | Check `list_models` output |
| `load failed` | Insufficient RAM | Unload other models first |
| `config set failed` | Hermes not installed | Install Hermes CLI |

## Notes

- **Non-destructive by default** — unload requires explicit `y` confirmation
- **Load polling** — max 60 seconds (30 iterations × 2s); aborts if model doesn't load
- **Config vs RAM** — oMLX loads model into memory; Hermes config points to it. Both must be correct.
- **Session reset** — Hermes reads model config at session start; run `/reset` after switching
- **Helper models** — `text_encoder`, `transformer`, `vae`, `MarkItDown` are helper models; don't unload them unless necessary
