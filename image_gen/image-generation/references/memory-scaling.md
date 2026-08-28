# Memory Scaling Reference

Measured on M-series Mac (64 GB unified memory) with FLUX.2 Klein 4B, quantize=8, 4 steps.

| Resolution | Peak MLX Memory | Time | Notes |
|-----------|----------------|------|-------|
| 512×512 | 10.52 GB | ~6s | Fast test |
| 1024×1024 | 17.95 GB | ~12s | Standard |
| 2048×2048 | 42.41 GB | ~63s | 4MP max |

### Scaling Pattern

Memory scales roughly **quadratically** with resolution (linear in pixel count):

```
512² = 262K pixels  → 10.5 GB
1024² = 1.05M pixels → 18.0 GB (4× pixels, 1.7× memory)
2048² = 4.19M pixels → 42.4 GB (16× pixels, 4× memory)
```

The non-linear factor comes from intermediate activation maps and KV cache growth.

### Planning for Available Memory

On a Mac with **N** GB RAM, the safe max resolution is where peak MLX memory stays below **N − 10 GB** (leaving room for OS).

| Mac RAM | Safe Max Resolution |
|---------|-------------------|
| 16 GB | 512×512 (use `--low-ram`) |
| 24 GB | 1024×1024 |
| 32 GB | 1024×1024 |
| 36 GB | 1024×1024 |
| 48 GB | 2048×2048 |
| 64 GB | 2048×2048 (comfortable) |
| 96 GB | 2048×2048 (very comfortable) |

### Reducing Memory Usage

1. **`--low-ram`** — enables aggressive caching, slower but works on 16 GB Macs
2. **`--mlx-cache-limit-gb 8`** — caps MLX cache at 8 GB without full low-ram mode
3. **Lower quantization** — `--quantize 4` reduces model weight memory
4. **Lower resolution** — most visible impact on memory
5. **Fewer steps** — distilled models at 4 steps vs base models at 50 steps
