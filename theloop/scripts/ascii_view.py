#!/usr/bin/env python3
"""ascii_view.py -- render an image to ASCII art so you can "see" it when no
vision tool (image-reading model) is exposed in the environment.

Usage:
  python3 ascii_view.py image.png                      # full image, ~120x50
  python3 ascii_view.py image.png 0,360,470,585        # crop box x1,y1,x2,y2
  python3 ascii_view.py image.png 0,360,470,585 160 80 # crop box + output W H

Reads any PIL-supported image, converts to grayscale, maps luminance to
" .:-=+*#%@" (dark->bright) and prints a text rendering you can judge by eye.
Use a crop box + larger W H to zoom into a detail (e.g. a cat's head) so its
features (ears, eyes, tail) survive the low resolution.
"""
import sys


def main(argv):
    if len(argv) < 2:
        print("usage: ascii_view.py image.png [box x1,y1,x2,y2] [W H]")
        return 2
    try:
        from PIL import Image
    except Exception as e:  # noqa: BLE001
        print("PIL not available:", e)
        return 2

    path = argv[1]
    box = None
    if len(argv) > 2 and "," in argv[2]:
        box = tuple(int(x) for x in argv[2].split(","))
    w_out, h_out = (int(argv[3]), int(argv[4])) if len(argv) > 4 else (120, 50)

    im = Image.open(path).convert("L")
    if box:
        im = im.crop(box)
    im = im.resize((w_out, h_out))

    chars = " .:-=+*#%@"
    n = len(chars)
    raw = im.tobytes()  # 'L' mode: 1 byte/pixel, no getdata() needed
    grid = []
    for i in range(h_out):
        line = raw[i * w_out:(i + 1) * w_out]
        grid.append("".join(chars[min(int(b / 256 * n), n - 1)] for b in line))
    print(path)
    for line in grid:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
