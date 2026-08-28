#!/usr/bin/env python3
"""Multi-reference image editing with FLUX.2 Klein 9B."""

import time
import os
import sys

MODEL_PATH = os.path.expanduser("~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit")


def generate_multi_reference(prompt, image_paths, output_path, width=1080, height=1350, seed=42):
    from mflux.models.flux2.variants import txt2img
    from mflux.models.common.config.model_config import ModelConfig

    config = ModelConfig.flux2_klein_9b()

    model = txt2img.Flux2Klein(
        model_path=MODEL_PATH,
        model_config=config,
    )

    start = time.time()
    result = model.generate_image(
        prompt=prompt,
        image_path=image_paths,
        image_strength=0.4,
        seed=seed,
        num_inference_steps=4,
        height=height,
        width=width,
        guidance=1.0,
    )
    elapsed = time.time() - start

    result.save(output_path)
    return output_path, elapsed


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else ""
    img1 = sys.argv[2] if len(sys.argv) > 2 else ""
    img2 = sys.argv[3] if len(sys.argv) > 3 else ""
    output = sys.argv[4] if len(sys.argv) > 4 else "/tmp/couple_kissing_9b.png"

    if not prompt or not img1 or not img2:
        print("Usage: python3 multi_ref_edit.py 'prompt' image1.jpg image2.jpg output.png")
        sys.exit(1)

    path, elapsed = generate_multi_reference(prompt, [img1, img2], output)
    print(f"Generated: {path} in {elapsed:.1f}s")
