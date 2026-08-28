#!/usr/bin/env python3
"""Generate an image using mflux FLUX.2 Klein 4B model."""

from mflux.models.flux2.variants import Flux2Klein
from mflux.models.common.config import ModelConfig

def generate_image(prompt: str, output_path: str = "output.png", seed: int = 42) -> str:
    """Generate an image and save to output_path.
    
    Args:
        prompt: Image description text
        output_path: Where to save the PNG
        seed: Random seed for reproducibility
    
    Returns:
        The output file path
    """
    # ⚠️ CRITICAL: model_config must be a ModelConfig object, NOT a string
    model = Flux2Klein(model_config=ModelConfig.flux2_klein_4b(), quantize=8)
    
    print(f"Generating: '{prompt}'")
    image = model.generate_image(
        prompt=prompt,
        seed=seed,
        num_inference_steps=8,
        width=2048,
        height=2048,
    )
    
    image.save(output_path)
    print(f"Saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    import sys
    prompt = sys.argv[1] if len(sys.argv) > 1 else "a cat watching sunset in the beach"
    output = sys.argv[2] if len(sys.argv) > 2 else "/tmp/output.png"
    generate_image(prompt, output)
