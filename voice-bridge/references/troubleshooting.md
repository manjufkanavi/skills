# Voice Bridge — Troubleshooting Guide

## Error: "INVALID_PROTOBUF : Load model failed"

**Symptom:** `onnxruntime.capi.onnxruntime_pybind11_state.InvalidProtobuf`

**Cause:** Pointing `Kokoro()` at a `.safetensors` file instead of `.onnx`. The LM Studio Kokoro model is in MLX safetensors format — kokoro-onnx requires ONNX.

**Fix:** Use the ONNX model from `onnx-community/Kokoro-82M-ONNX` on HuggingFace:

```bash
python3 -c "
from huggingface_hub import hf_hub_download
hf_hub_download('onnx-community/Kokoro-82M-ONNX', 'onnx/model.onnx', local_dir='/tmp/kokoro')
hf_hub_download('onnx-community/Kokoro-82M-ONNX', 'tokenizer.json', local_dir='/tmp/kokoro')
hf_hub_download('onnx-community/Kokoro-82M-ONNX', 'tokenizer_config.json', local_dir='/tmp/kokoro')
"
curl -sL https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin -o /tmp/voices-v1.0.bin
```

## Error: "IsADirectoryError: voices path is a directory"

**Symptom:** `np.load(voices_path)` fails because passed a directory.

**Fix:** Pass a single `.bin` file: `Kokoro(model_path, '/path/to/voices-v1.0.bin')`

## Error: "INVALID_ARGUMENT ... Unexpected input data type"

**Symptom:** ONNX runtime type mismatch (int32 vs float) or wrong dimensions.

**Root causes:**
1. **Voice shape:** Kokoro voices are `(510, 1, 256)`, model expects `(1, 256)`. Always use `mean(axis=0)`.
2. **Token dtype:** `input_ids` must be `np.int64`.
3. **Speed dtype:** must be `np.float32`.

**Fix:**
```python
inputs = {
    'input_ids': tokens.reshape(1, -1),        # np.int64
    'style': style.reshape(1, -1),              # np.float32
    'speed': np.array([speed], dtype=np.float32),
}
```

## Error: "text is too long, must be less than 510 phonemes"

**Cause:** Kokoro's 510-phoneme context limit. Responses longer than ~400 chars get truncated at sentence boundary. Already handled in `voice_bridge.py`.

## Error: "voices file not found" / pickle load error

**Symptom:** `af.bin` from HF Hub fails with pickle errors in newer numpy.

**Fix:** Use `voices-v1.0.bin` from the official kokoro-onnx releases instead of HF Hub voice files.

## MLX Whisper

**API:** `mlx_whisper.transcribe(file, path_or_hf_repo=model_path)` — NOT `model_path=`, use `path_or_hf_repo=`.

## Performance

| Operation | First Run | Subsequent |
|-----------|-----------|------------|
| Kokoro model load | ~2s | cached |
| Kokoro TTS (short text) | — | ~0.5s |
| Whisper transcription | ~2s | warm |
| Full STT → LLM → TTS loop | — | ~3-5s total |

Kokoro runs on CPU only (onnxruntime CPUExecutionProvider) — no GPU on Apple Silicon.

## Supported Input Formats

Telegram voice notes: `.oga` (Opus), `.m4a` (AAC), `.ogg` (Vorbis), `.wav`, `.mp3`.
All convert to 16kHz mono WAV via ffmpeg for Whisper.