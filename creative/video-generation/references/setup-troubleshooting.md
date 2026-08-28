# FastMetal-QAD Setup Troubleshooting

Real-world issues encountered during testing and their fixes.

## GitHub URL Mismatch

**Problem:** HuggingFace model pages reference `https://github.com/FastVideo/FastVideo.git` but this repo returns 404.

**Fix:** The correct URL is `https://github.com/hao-ai-lab/fastvideo`.

```bash
git clone https://github.com/hao-ai-lab/fastvideo.git ~/.studio/FastVideo
```

## transformer/config.json Missing

**Problem:** The inference scripts (`mlx_wan_prompt_to_video.py`, `mlx_wan22_generate.py`) read `transformer/config.json` from the model root, but FastMetal-QAD models only have `mlx_dit.json` at the root level.

**Fix:** Create the expected file by copying `mlx_dit.json`:

```bash
mkdir -p ~/.lmstudio/models/FastMetal-1.3B-QAD/transformer
cp ~/.lmstudio/models/FastMetal-1.3B-QAD/mlx_dit.json ~/.lmstudio/models/FastMetal-1.3B-QAD/transformer/config.json

mkdir -p ~/.lmstudio/models/FastMetal-5B-QAD/transformer
cp ~/.lmstudio/models/FastMetal-5B-QAD/mlx_dit.json ~/.lmstudio/models/FastMetal-5B-QAD/transformer/config.json
```

This is a one-time setup step. The `config.json` is only read to extract architecture parameters (in_channels, out_channels, patch_size) — the actual DiT weights come from `mlx_dit.safetensors` via `--mlx-checkpoint`.

## hfdl `--optimize-download` Flag Not Recognized

**Problem:** `hfdl: error: unrecognized arguments: --optimize-download`

**Fix:** This flag does not exist in hfdl 0.4.0. Omit it from all commands.

```bash
# WRONG
hfdl FastVideo/FastMetal-1.3B-QAD -r model -d ~/.lmstudio/models -t auto --optimize-download

# CORRECT
hfdl FastVideo/FastMetal-1.3B-QAD -r model -d ~/.lmstudio/models -t auto
```

## Model Download Path

**Problem:** The skill initially assumed models would be nested under `~/.lmstudio/models/FastMetal-QAD/FastVideo/FastMetal-1.3B-QAD/`.

**Fix:** hfdl downloads models directly to `~/.lmstudio/models/FastMetal-1.3B-QAD/` (flat structure). Update all path references accordingly.

## Python 3.14 / PyO3 Compatibility

**Problem:** `pydantic-core` build fails on Python 3.14: "the configured Python interpreter version (3.14) is newer than PyO3's maximum supported version (3.13)".

**Fix:** If building from source fails, `pydantic-core` may already be installed. Use `--no-build-isolation` or `--no-deps` to skip rebuilding it:

```bash
python3 -m pip install -e ".[mlx]" --break-system-packages --no-build-isolation
```

## Actual Benchmarks (vs Documented)

Documented benchmarks (M4 Max 36 GB):
- 1.3B: 110s end-to-end, 90s denoise only
- 5B: 151s end-to-end, 98s denoise only

Actual benchmarks (same hardware, with `--fast` flag):
- 1.3B: **52.7s** total (24.6s denoise + 12.6s prompt encode + 9.4s decode + 5.9s RIFE post)
- 5B: **54.8s** total (16.8s denoise + 32.1s prompt encode + 2.8s decode + 2.4s RIFE post)

The `--fast` flag enables RIFE frame interpolation (2x) and resolution optimization, cutting total time roughly in half.

## Memory Usage

Documented peak memory:
- 1.3B: 3.87 GiB
- 5B: 9.34 GiB

Actual peak memory (measured):
- 1.3B: **3.20 GiB** (denoise phase)
- 5B: **6.85 GiB** (denoise phase)

Both models fit comfortably in 16 GB Macs. The 5B model's lower-than-expected memory is due to the `--fast` flag reducing resolution during denoising.

## Model-Specific Scripts

- **1.3B:** Uses `examples/inference/basic/mlx_wan_prompt_to_video.py`
- **5B:** Uses `examples/inference/basic/mlx_wan22_generate.py` (different script, different API)

The 5B model's script has a different argument structure:
- `--text-encoder-root` instead of `--model-root`
- `--vae-root` for VAE path
- `--dit-checkpoint` / `--dit-config` for DiT
- `--mlx-checkpoint` for pre-quantized MLX checkpoint

## AV Library Conflict Warning

```
objc[PID]: Class AVFFrameReceiver is implemented in both
/opt/homebrew/lib/python3.14/site-packages/av/.dylibs/libavdevice.62.3.102.dylib
and /opt/homebrew/lib/python3.14/site-packages/cv2/.dylibs/libavdevice.61.3.100.dylib
```

This is a harmless warning from conflicting `libavdevice` versions between `av` and `cv2` packages. It does not affect video generation output.
