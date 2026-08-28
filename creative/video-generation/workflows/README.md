# Workflows

FastMetal-QAD uses MLX-native Python inference scripts — no ComfyUI workflow JSON needed.

The generation scripts (`generate_video.py`) call FastVideo's inference scripts directly:

- **1.3B:** `examples/inference/basic/mlx_wan_prompt_to_video.py`
- **5B:** `examples/inference/basic/mlx_wan22_generate.py`

These are cloned from the FastVideo repository during setup.
