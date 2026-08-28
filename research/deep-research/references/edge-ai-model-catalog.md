# Sub-1B On-Device Model Catalog

Condensed reference of models <1B parameters that run without GPU on edge devices (CPU, NPU, DSP, microcontroller). Updated August 2026.

## TTS (Text-to-Speech)

| Model | Params | Languages | Notes |
|-------|--------|-----------|-------|
| Kokoro | ~150M | 16+ | Fast, high-quality, ONNX/TensorRT. Voice: af_bella, af_sarah |
| Piper | ~15M | 20+ | Extremely lightweight, real-time, Rust-based |
| Coqui TTS (XTTS-v2 distilled) | ~300M | 16 | Voice cloning, multi-lingual, ~600MB RAM |
| VITS | ~60M | 1 | Single-voice, high quality, fast CPU |
| FastSpeech 2 (small) | ~50M | 1-2 | Non-autoregressive, fast production TTS |
| Matcha-TTS | ~40M | 1 | Flow-based, fast, high quality |

## OCR (Optical Character Recognition)

| Model | Params | Notes |
|-------|--------|-------|
| PaddleOCR PP-OCRv4 | ~25M total | Best overall, 20M detection + 5M recognition |
| Surya OCR | ~100M | Layout-aware, complex documents |
| EasyOCR | ~35M | 80+ languages, easy API |
| Tesseract 5 (LSTM) | ~50M | Classic, 100+ languages |
| TrOCR (small) | ~135M | Transformer-based, handwritten text |

## Speech Recognition (ASR)

| Model | Params | Languages | Notes |
|-------|--------|-----------|-------|
| Moonshine | 27M–331M | English (expanding) | Whisper-level accuracy, edge-optimized |
| Vosk (Kaldi) | ~50M | 20+ | Offline, real-time, Raspberry Pi proven |
| Whisper Tiny | 39M | 99+ | OpenAI, multilingual |
| Whisper Base | 74M | 99+ | Better accuracy, very fast |
| Whisper Small | 244M | 99+ | Good speed/accuracy balance on CPU |
| Paraformer-small | ~80M | 20+ | Alibaba, streaming ASR |

## Text Generation (SLMs)

| Model | Params | Notes |
|-------|--------|-------|
| Gemma 3n 270M | 270M | Google, multimodal (text/image/audio/video), LiteRT |
| Gemma 3 1B | 1B | Google AI Edge, text-only |
| Qwen2.5-0.5B | 500M | Strong reasoning, coding, multilingual |
| SmolLM2 135M | 135M | Hugging Face, multilingual, very fast |
| SmolLM2 360M | 360M | Better reasoning, still fast |
| GPT-2 small | 125M | Classic, limited but functional |
| MicroLM | 10M–100M | TinyStories-trained, very small |

## Image Classification

| Model | Params | Notes |
|-------|--------|-------|
| MobileNetV3-Small | ~2.5M | Industry standard, ImageNet 1000 classes |
| MobileNetV2 | ~3.5M | Classic, well-supported everywhere |
| EfficientNet-B0 | ~5.3M | Best accuracy/params ratio |
| ShuffleNetV2 | ~1.3M | Ultra-lightweight |
| SqueezeNet 1.1 | ~1.2M | AlexNet-level accuracy, 50x fewer params |
| LeNet | ~0.6M | Classic MNIST, runs on any MCU |

## Object Detection

| Model | Params | Notes |
|-------|--------|-------|
| YOLOv8n | ~3.2M | Fastest YOLO, COCO mAP 37.3% |
| YOLOv9-Tiny | ~2.1M | Very fast, good accuracy |
| YOLOX-Nano | ~1M | Anchor-free, very small |
| NanoDet | ~2M | Ultra-lightweight, no anchor |
| BlazeFace | ~0.5M | Google, face detection only |

## Pose Estimation

| Model | Params | Notes |
|-------|--------|-------|
| MoveNet SinglePose | ~6M | Google, single person, real-time |
| MoveNet MultiPose | ~20M | Multi-person pose estimation |
| YOLO-Pose | ~3.2M | Based on YOLOv8n, 17 keypoints |

## Face Recognition

| Model | Params | Notes |
|-------|--------|-------|
| ArcFace (MobileFaceNet) | ~0.8M | SOTA accuracy/size |
| FaceNet (Inception-ResNet-v1) | ~5.5M | Google, well-known |
| GhostFaceNet | ~1.5M | Ghost modules for efficiency |

## Translation

| Model | Params | Languages | Notes |
|-------|--------|-----------|-------|
| NLLB-200-distilled-600M | 600M | 200 | Facebook, excellent multilingual |
| mBART base | ~610M | 50+ | Fair quality |
| T5-Small | ~250M | 12 | Decent |
| BART (base) | ~400M | 16 | Good for NMT |

## Embedding Models

| Model | Params | Dimensions | Notes |
|-------|--------|-----------|-------|
| all-MiniLM-L6-v2 | ~22M | 384 | Best small embedding, SentenceTransformers |
| bge-small-en-v1.5 | ~33M | 512 | BAAI, strong multilingual |
| E5-small-v2 | ~33M | 384 | Microsoft, good for retrieval |
| GTE-small | ~33M | 384 | Alibaba, strong retrieval |

## Keyword Spotting

| Model | Params | Notes |
|-------|--------|-------|
| TinyML KWS | ~10K–100K | TensorFlow Lite, runs on any MCU |
| YAMNet | ~6M | Google, audio event classification |
| PANNs (small) | ~5M | Audio neural networks, 527 classes |

## Deployment Frameworks

| Runtime | Platforms |
|---------|-----------|
| ONNX Runtime | All platforms |
| TensorFlow Lite | Android, iOS, MCU |
| Apple MLX | Apple Silicon (Mac, iPhone, iPad) |
| OpenVINO | Intel, ARM CPUs |
| Google LiteRT | Android, Raspberry Pi |
| TFLite Micro | MCU, ESP32, STM32 |
| NCNN | Mobile, embedded (Tencent) |
| MNN | Mobile, embedded (Alibaba) |

## Hardware Sweet Spots

| Device | Best Models | RAM |
|--------|------------|-----|
| ESP32-S3 | TinyML KWS, LeNet, BlazeFace | 512KB–2MB |
| Pi Zero 2W | Whisper Tiny, MobileNetV3, YOLOv8n | 512MB–1GB |
| Pi 4 (4GB) | Whisper Small, YOLOv8, Gemma 270M | 1–2GB |
| Pi 5 (8GB) | Gemma 1B, Whisper Small, SD 1.5 (int4) | 2–4GB |
| iPhone (A15+) | All CoreML, Kokoro, Whisper | 4–8GB |
| Mac (M-series) | All MLX, Gemma 1B, SD 1.5 | 8–16GB |
