# Kokoto TTS (kokoro_onnx) in the pipeline

## Layout
- Model: `~/.hermes/skills/voice-bridge/assets/kokoro/model.onnx` (~325 MB, 54 voices).
- Voices: `~/.hermes/skills/voice-bridge/assets/voices-v1.0.bin` (~28 MB).
- Python package: `kokoro_onnx` (installed in `~/.venvs/infographic-show`).

## Bug: voice embedding lookup
Wrong:
```python
voice_emb = k.voices.get(voice) or k.voices.get("af_bella")
```
Fails with:
```
ValueError: The truth value of an array with more than one element is ambiguous.
```
because `k.voices.get()` returns a **numpy array**, whose truth value is ambiguous.

Fix — check `is None`:
```python
voice_emb = k.voices.get(voice)
if voice_emb is None:
    voice_emb = k.voices.get("af_bella")
```

## Optional
Kokoto is optional: if the package is missing, narration is skipped and the video is silent (scenes still hold for their duration). The script degrades gracefully rather than crashing.
