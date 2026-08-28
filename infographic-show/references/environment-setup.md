# Environment setup for the infographic-show venv

Notes for running the skill venv (`.venvs/infographic-show`, Python 3.11) on this host.

## Installing packages - use `uv pip install --python <venv>/bin/python`

The skill venv is pip-less (uv-managed, PEP 668). There is no `bin/pip`. The `--venv`
flag on `uv pip install` is invalid and errors with `unexpected argument '--venv'`.

Target the venv by its interpreter with `--python`:

```bash
uv pip install --python ~/.venvs/infographic-show/bin/python cairosvg Pillow
uv pip install --python ~/.venvs/infographic-show/bin/python onnxruntime kokoro_onnx soundfile
```

Verify the stack loaded:
```bash
~/.venvs/infographic-show/bin/python -c "import cairosvg, numpy, soundfile; print('render stack OK')"
~/.venvs/infographic-show/bin/python -c "import onnxruntime, kokoro_onnx; print('TTS stack OK')"
```

## Render with the cairosvg CLI - NOT the `svg2png()` Python API

`generate_video.py` rasterizes via the cairosvg CLI, passing size with `-W`/`-H`:

```bash
cairosvg input.svg -o out.png -W 1920 -H 1080
```

Do not use the Python `cairosvg.svg2png(url=..., write_to=...)` API with `width`/`height`
kwargs - it raises `TypeError: svg2png() got an unexpected keyword argument 'width'`. Use the CLI.

## Background-process execution requires absolute paths

When a skill script is invoked from a background process, its working directory is the
shell cwd (the user home dir), not the skill directory. So a relative path like
`scripts/research_to_video.py` resolves to `<home>/scripts/...` and fails with
`can't open file`.

Always pass absolute paths to the script and to any data files:

```bash
~/.venvs/infographic-show/bin/python /abs/path/to/scripts/research_to_video.py --script /abs/path/to/scripts/scenes_plan.json --output /tmp/out.mp4
```

`research_to_video.py` already resolves the deep-research skill by absolute candidate paths, but the entry invocation itself must be absolute.