#!/usr/bin/env python3
"""Convert SVG string to JPEG and save to generated_images directory."""

import sys
import os
import hashlib
import datetime

try:
    import cairosvg
    from PIL import Image
    import io
except ImportError:
    print("ERROR: cairosvg and Pillow are required. Install with: pip install cairosvg Pillow", file=sys.stderr)
    sys.exit(1)


def svg_to_jpeg(svg_string: str, output_dir: str = None, width: int = 1024, height: int = 1024, quality: int = 95) -> str:
    """
    Convert an SVG string to a JPEG image.

    Args:
        svg_string: Raw SVG content as a string.
        output_dir: Directory to save the JPEG. Defaults to ./generated_images.
        width: Output width in pixels.
        height: Output height in pixels.
        quality: JPEG quality (1-100).

    Returns:
        Path to the generated JPEG file.
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_images")

    os.makedirs(output_dir, exist_ok=True)

    # Generate filename from SVG content hash + timestamp
    content_hash = hashlib.md5(svg_string.encode("utf-8")).hexdigest()[:12]
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"svg-{timestamp}-{content_hash}.jpg"
    output_path = os.path.join(output_dir, filename)

    # Convert SVG to PNG via cairosvg
    png_data = cairosvg.svg2png(
        bytestring=svg_string.encode("utf-8"),
        output_width=width,
        output_height=height,
    )

    # Convert PNG to JPEG via Pillow
    img = Image.open(io.BytesIO(png_data))
    # Ensure RGB mode (JPEG doesn't support RGBA)
    if img.mode == "RGBA":
        img = img.convert("RGB")
    elif img.mode == "P":
        img = img.convert("RGB")

    img.save(output_path, format="JPEG", quality=quality, optimize=True)

    file_size = os.path.getsize(output_path)
    print(f"Generated: {output_path} ({file_size:,} bytes)")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: svg_to_jpeg.py <svg_file_or_string> [output_dir] [width] [height] [quality]")
        print("  If argument is a file path, reads SVG from file.")
        print("  If argument starts with '<', treats as raw SVG string.")
        print("  Otherwise treats as raw SVG string.")
        sys.exit(1)

    arg = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    height = int(sys.argv[4]) if len(sys.argv) > 4 else 1024
    quality = int(sys.argv[5]) if len(sys.argv) > 5 else 95

    if arg.startswith("<"):
        svg_content = arg
    elif os.path.isfile(arg):
        with open(arg, "r") as f:
            svg_content = f.read()
    else:
        svg_content = arg

    output_path = svg_to_jpeg(svg_content, output_dir, width, height, quality)
    print(f"Output: {output_path}")
