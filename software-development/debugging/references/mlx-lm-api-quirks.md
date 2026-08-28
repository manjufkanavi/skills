# MLX LM API Quirks — Quick Reference

## `mlx_lm.generate()` Does NOT Accept `temperature`

The `generate()` function from `mlx_lm` does **NOT** accept `temperature` as a keyword argument, even though it appears in the function signature documentation.

```python
# WRONG — raises TypeError: generate_step() got an unexpected keyword argument 'temperature'
response = generate(model, tokenizer, prompt=prompt, max_tokens=1024, temperature=0.3)

# CORRECT — omit temperature entirely
response = generate(model, tokenizer, prompt=prompt, max_tokens=1024, verbose=False)
```

**Workaround**: If you need temperature control, use `stream_generate()` with temperature in kwargs, or load the model with a different inference path.

## Model Loading Time

A 3B parameter model in 8-bit quantization takes **2–4 minutes** to load on CPU. Plan accordingly:
- Never run model loading in a short-timeout foreground process
- Use `background=true` with `notify_on_complete=true` for loading
- Print status BEFORE loading starts so the user knows something is happening

## LoRA Adapter Loading

When loading a fine-tuned model with LoRA adapters:

```python
from train_solvarch import add_lora_to_model, load_checkpoint

model, tokenizer = load(MODEL_PATH)
hidden_size = model.args.hidden_size
model.freeze()  # Freeze base model before adding LoRA
model, _, _ = add_lora_to_model(model, RANK, ALPHA, DROPOUT, hidden_size)
load_checkpoint(model, Path("trained-model/final"))
```

**Key**: `model.freeze()` MUST come before `add_lora_to_model()`, otherwise the LoRA weights get overridden by frozen weights.

## Set vs List for Service Comparison

When comparing AWS services between base and fine-tuned model outputs, the result lists are **lists**, not sets. The `&` operator does NOT work on lists:

```python
# WRONG — TypeError: unsupported operand type(s) for &: 'list' and 'list'
common = results['base_all_services'] & results['ft_all_services']

# CORRECT
common = set(results['base_all_services']) & set(results['ft_all_services'])
```
