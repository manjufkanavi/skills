# Voice Bridge — Technical Notes

## Model Paths

| Model | Location | Format |
|-------|----------|--------|
| Whisper | `~/.lmstudio/models/mlx-community/whisper-large-v3-turbo/` | MLX (safetensors) |
| Kokoro | `~/.hermes/skills/voice-bridge/assets/kokoro/model.onnx` | ONNX (int64) |
| Voices | `~/.hermes/skills/voice-bridge/assets/voices-v1.0.bin` | Pickle .npz |

## Why ONNX for Kokoro?

The Kokoro model downloaded from LM Studio is in MLX safetensors format (`kokoro-v1_0.safetensors`). The `kokoro-onnx` library requires ONNX format for inference. We downloaded the ONNX variant from HuggingFace (`onnx-community/Kokoro-82M-ONNX`).

## Audio Format Handling

1. **Input**: Telegram voice notes (m4a, oga, ogg) → ffmpeg → 16kHz mono WAV (whisper requirement)
2. **Output**: Kokoro → 24kHz stereo → scipy → .wav → ffmpeg → .oga (opus, better for Telegram)

## Voice Embedding Quirk

Kokoro voice embeddings are `(510, 1, 256)` — 510 time steps × 1 channel × 256 dims.
The model expects `(1, 256)` for the `style` input. We take `mean(axis=0)` to collapse.

## Known Issues

- MLX Whisper detects language from short clips; may misidentify (e.g., Slovenian for English)
- First TTS call warms up model (~2s). Subsequent calls are ~1s.
- Onnxruntime CPU only on macOS Apple Silicon (no GPU provider available)
