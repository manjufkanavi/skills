# macOS libcairo for cairosvg

## Problem
On macOS, `cairosvg` (via `cairocffi`) crashes when rasterizing SVG → PNG:
```
OSError: no library called "cairo-2" was found
cannot load library 'libcairo.so.2': dlopen(...): tried: ...
```
`dlopen` / `ctypes.util.find_library()` cannot locate Homebrew's `libcairo.2.dylib` — it is not on `DYLD_LIBRARY_PATH` and not in the dyld cache.

## Fix
Set `DYLD_LIBRARY_PATH=/opt/homebrew/lib` before invoking cairosvg. Homebrew's `libcairo.2.dylib` lives at `/opt/homebrew/lib/libcairo.2.dylib`.

Verify:
```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
cairosvg input.svg -o out.png -W 1920 -H 1080   # now succeeds
python -c "import cairosvg"                      # import now succeeds
```

## How the script handles it
`generate_video.py` sets `os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/lib"` at import time (guarded by `os.path.isdir("/opt/homebrew/lib")`), so no manual export is needed.

## Gotcha
The nested `except subprocess.CalledProcessError` fallback in `render_scene_to_png` **swallows** the error, so if cairosvg fails silently, **no PNG is produced** and the later ffmpeg step fails with missing inputs. Symptom to watch: the video build fails but no PNG files exist in the work dir.
