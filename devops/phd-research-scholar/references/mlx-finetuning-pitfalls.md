# MLX Fine-Tuning Pitfalls

## PEFT Incompatibility with MLX Models

**Problem:** `peft.get_peft_model(model, config)` fails with:
```
AttributeError: 'Model' object has no attribute 'get_submodule'
```

**Cause:** PEFT is designed for HuggingFace `nn.Module` models. MLX models use a different architecture without `get_submodule()`.

**Solution:** Use MLX-native LoRA implementation:
```python
import mlx.core as mc
import mlx.nn as nn
import mlx.optimizers as optim

# Manual LoRA on existing layers
class LoRALinear(nn.Module):
    def __init__(self, in_features, out_features, rank=16):
        self.linear = nn.Linear(in_features, out_features)
        self.lora_a = nn.Linear(in_features, rank, bias=False)
        self.lora_b = nn.Linear(rank, out_features, bias=False)
        self.scale = rank ** -0.5

    def __call__(self, x):
        return self.linear(x) + self.lora_b(self.lora_a(x)) * self.scale

# Or use mlx.lora if available in newer versions
```

## mlx_lm.generate Parameter Quirks

**Problem:** `generate(model, tokenizer, prompt, temperature=0.1)` fails with:
```
TypeError: generate_step() got an unexpected keyword argument 'temperature'
```

**Solution:** Use correct parameters:
```python
from mlx_lm import generate, stream_generate

# Correct — no temperature/top_p as kwargs
response = generate(model, tokenizer, prompt="...", max_tokens=200)

# For controlled sampling, use stream_generate with sampler
from mlx_lm.sample_utils import make_sampler
sampler = make_sampler("top_p", 0.9)
for token in stream_generate(model, tokenizer, tokens, max_tokens=200, sampler=sampler):
    print(tokenizer.decode([token]), end="", flush=True)
```

## MLX Training Loop Pattern

```python
import mlx.core as mc
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np

# Loss function with gradient
def train_step(model, batch_ids, batch_mask, optimizer):
    def loss_fn(params):
        model.update_params(params)
        loss, _ = model.loss("causal_lm", batch_ids, batch_mask, return_params=False)
        return loss
    loss, grad = mc.value_and_grad(model, loss_fn)()
    optimizer.update(model, grad)
    return float(loss)

# Training loop with gradient accumulation
for epoch in range(num_epochs):
    for batch_start in range(0, len(examples), batch_size * accumulation):
        batch = get_batch(batch_start)
        loss = train_step(model, batch.ids, batch.mask, optimizer)
        if step % accumulation == 0:
            optimizer.step()
```

## Model Download & Cache

```python
from huggingface_hub import snapshot_download

# Download MLX-quantized model
path = snapshot_download(
    'mlx-community/Qwen2.5-Coder-3B-Instruct-8bit',
    local_dir='/Users/manjunathkanavi/.models/Qwen2.5-Coder-3B-Instruct-8bit'
)

# Load
from mlx_lm import load
model, tokenizer = load(path)
```

## Venv for MLX Tools

Path: `/Users/manjunathkanavi/workspace/scripts/python_venv/`

Packages: `mlx`, `mlx-lm`, `mlx-metal`, `transformers`, `peft`, `accelerate`, `torch`

Use this venv for all MLX/transformers work to avoid PEP 668 conflicts.
