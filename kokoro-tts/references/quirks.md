# Kokoro TTS — Gotchas & Quirks

## API

- **Method is `k.create()`, NOT `k.generate()`** — `generate()` does not exist
- **Voice embedding as `voice` parameter**, not `style` — pass numpy array directly as `voice=style`
- **Voice lookup bug**: `k.voices.get(voice)` returns a numpy array, whose truth value is ambiguous. Always use `is None`:
  ```python
  voice_emb = k.voices.get(voice)
  if voice_emb is None:
      voice_emb = k.voices.get("af_bella")
  ```

## Audio Shape

- Output is `(1, N)` — must flatten to `(N,)` before saving
- Save with scipy: `wavfile.write(path, sr, audio.flatten().astype('float32'))`

## ONNX Types

- `input_ids` must be `int64`
- `speed` must be `float32`
- `kokoro-onnx` auto-converts, but custom inference needs explicit types:
  ```python
  inputs = {
      'input_ids': tokens.reshape(1, -1),        # np.int64
      'style': style.reshape(1, -1),              # np.float32
      'speed': np.array([speed], dtype=np.float32),
  }
  ```

## Context Limit

- 510-phoneme context length
- ~400 chars per segment before truncation
- Split text at sentence boundaries for best results

## Model Files

- ONNX model from `onnx-community/Kokoro-82M-ONNX` on HuggingFace
- **Safetensors model will NOT work** with `kokoro-onnx` — fails with protobuf parsing error
- Place model files permanently in skill assets, not `/tmp/`

## Performance

- First TTS call loads model into memory (~2s)
- Subsequent calls are faster (model stays loaded)
- For batch generation, reuse the same `Kokoro` instance
