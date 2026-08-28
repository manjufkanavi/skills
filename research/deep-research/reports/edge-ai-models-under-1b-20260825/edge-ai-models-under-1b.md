# Small On-Device AI Models Under 1B Parameters — Comprehensive Research Report

> **Date:** August 25, 2026
> **Scope:** Models <1B parameters that run without GPU on edge devices (CPU, NPU, DSP, microcontroller)
> **Categories:** TTS, OCR, Speech Recognition, Image Classification, Object Detection, Text Generation, Translation, Audio Generation, Pose Estimation, Face Recognition, Embedding Models, and more

---

## Executive Summary

The landscape of sub-1B parameter on-device AI models has matured dramatically. Models now run on Raspberry Pi, smartphones, microcontrollers, and embedded boards — **without any GPU** — using CPU inference, hardware NPUs, or DSPs. This report catalogs the best models across 15+ categories, organized by parameter count and deployment target.

---

## 1. Text-to-Speech (TTS)

| Model | Parameters | Languages | On-Device? | Notes |
|-------|-----------|-----------|------------|-------|
| **Kokoro** | ~150M | 16+ | ✅ Yes | Fast, high-quality, ONNX/TensorRT support. Voice: af_bella, af_sarah, etc. |
| **Piper** | ~15M | 20+ | ✅ Yes | Extremely lightweight, real-time, Rust-based. Best for microcontrollers. |
| **Coqui TTS (XTTS-v2 distilled)** | ~300M | 16 | ✅ Yes | Voice cloning, multi-lingual. Requires ~600MB RAM. |
| **Bark (small)** | ~300M | English | ✅ Yes | Generative TTS with prosody control. Slower but expressive. |
| **VITS** | ~60M | 1 | ✅ Yes | Single-voice, high quality. Fast inference on CPU. |
| **FastSpeech 2 (small)** | ~50M | 1-2 | ✅ Yes | Non-autoregressive, fast. Good for production TTS. |
| **Matcha-TTS** | ~40M | 1 | ✅ Yes | Flow-based, fast, high quality. |
| **StyleTTS 2** | ~60M | 1 | ✅ Yes | Style control, natural prosody. |

**Best for Raspberry Pi / CPU:** Piper (15M) or Kokoro (150M)
**Best quality:** Kokoro or Coqui distilled

---

## 2. Optical Character Recognition (OCR)

| Model | Parameters | On-Device? | Notes |
|-------|-----------|------------|-------|
| **PaddleOCR (PP-OCRv4)** | ~20M (detection) + ~5M (recognition) | ✅ Yes | Best overall. Works on CPU. 20M+ languages. |
| **Surya OCR** | ~100M | ✅ Yes | Layout-aware, handles complex documents. |
| **EasyOCR** | ~15M (CRAFT) + ~20M (CRNN) | ✅ Yes | 80+ languages, easy API. |
| **Tesseract 5 (LSTM)** | ~50M | ✅ Yes | Classic, well-maintained, 100+ languages. |
| **TrOCR (small)** | ~135M | ✅ Yes | Transformer-based, good for handwritten text. |
| **Nougat (small)** | ~250M | ⚠️ Limited | PDF-to-Markdown. Needs ~1GB RAM. |

**Best for simple text:** PaddleOCR PP-OCRv4 (~25M total)
**Best for complex layouts:** Surya OCR (~100M)

---

## 3. Speech Recognition (ASR)

| Model | Parameters | Languages | On-Device? | Notes |
|-------|-----------|-----------|------------|-------|
| **Moonshine** | 27M–331M | English (expanding) | ✅ Yes | Whisper-level accuracy, edge-optimized. |
| **Vosk (Kaldi-based)** | ~50M | 20+ | ✅ Yes | Offline, real-time, Raspberry Pi proven. |
| **Whisper Tiny** | 39M | 99+ | ✅ Yes | OpenAI, multilingual, decent accuracy. |
| **Whisper Base** | 74M | 99+ | ✅ Yes | Better accuracy, still very fast. |
| **Whisper Small** | 244M | 99+ | ✅ Yes | Good balance of speed/accuracy on CPU. |
| **Paraformer-small (FunASR)** | ~80M | 20+ | ✅ Yes | Alibaba, streaming ASR. |
| **Nemo Stt_CTC** | ~100M | 1 | ✅ Yes | NVIDIA, high accuracy English ASR. |
| **Marblar** | ~60M | 1 | ✅ Yes | Fast, streaming, low-latency. |

**Best for Raspberry Pi:** Vosk (~50M) or Moonshine 27M
**Best multilingual:** Whisper Small (244M)

---

## 4. Text Generation (Small Language Models)

| Model | Parameters | On-Device? | Notes |
|-------|-----------|------------|-------|
| **Gemma 3n 270M** | 270M | ✅ Yes | Google, multimodal (text/image/audio/video), LiteRT optimized. |
| **Gemma 2B** | 2B | ⚠️ Limited | 2B is above 1B but runs on Pi 5 with int4 quantization. |
| **Qwen2.5-0.5B** | 500M | ✅ Yes | Strong reasoning, coding, multilingual. |
| **Qwen2.5-1.5B** | 1.5B | ⚠️ Limited | Runs on Pi 5 with int4 (~1.5GB RAM). |
| **Phi-3-mini** | 3.8B | ❌ No | Too large for most edge devices. |
| **Phi-3-small** | 1.1B | ⚠️ Limited | Near 1B, runs on Pi 5 with quantization. |
| **StableLM 2 1.2B** | 1.2B | ⚠️ Limited | Good general-purpose SLM. |
| **MicroLM** | 10M–100M | ✅ Yes | TinyStories-trained, very small. |
| **GPT-2 small** | 125M | ✅ Yes | Classic, limited but functional. |
| **NanoGPT** | 10M–100M | ✅ Yes | Minimal transformer, educational. |
| **SmolLM2 135M** | 135M | ✅ Yes | Hugging Face, multilingual, very fast. |
| **SmolLM2 360M** | 360M | ✅ Yes | Better reasoning, still fast. |
| **SmolLM2 1.7B** | 1.7B | ⚠️ Limited | Best SmolLM for Pi 5. |
| **Qwen3-1.7B** | 1.7B | ⚠️ Limited | Strong multilingual SLM. |
| **Gemma 3 270M** | 270M | ✅ Yes | Google AI Edge, first multimodal SLM on-device. |
| **Gemma 3 1B** | 1B | ✅ Yes | Google AI Edge, text-only variant. |
| **Gemma 3 4B** | 4B | ❌ No | Too large for most edge. |
| **Gemma 3n 270M** | 270M | ✅ Yes | Multimodal: text, image, video, audio. |

**Best under 1B:** Gemma 3n 270M (multimodal) or Qwen2.5-0.5B
**Best reasoning:** Qwen2.5-0.5B or SmolLM2 360M

---

## 5. Image Classification

| Model | Parameters | On-Device? | Notes |
|-------|-----------|------------|-------|
| **MobileNetV3-Small** | ~2.5M | ✅ Yes | Industry standard, ImageNet 1000 classes. |
| **MobileNetV3-Large** | ~5.5M | ✅ Yes | Better accuracy, still very fast. |
| **MobileNetV2** | ~3.5M | ✅ Yes | Classic, well-supported everywhere. |
| **EfficientNet-B0** | ~5.3M | ✅ Yes | Best accuracy/params ratio. |
| **EfficientNet-Lite** | ~5M | ✅ Yes | Mobile-optimized variant. |
| **ShuffleNetV2** | ~1.3M | ✅ Yes | Ultra-lightweight, 1M+ classes. |
| **ShuffleNetV2-x0.5** | ~1.3M | ✅ Yes | For microcontrollers. |
| **SqueezeNet 1.1** | ~1.2M | ✅ Yes | AlexNet-level accuracy, 50x fewer params. |
| **LeNet** | ~0.6M | ✅ Yes | Classic MNIST, runs on any MCU. |
| **YOLO-NAS-Small** | ~22M | ✅ Yes | Also does object detection. |
| **EdgeNeXt** | ~5M | ✅ Yes | Modern, CNN + attention hybrid. |
| **MobileViT-Small** | ~2.3M | ✅ Yes | Lightweight transformer for vision. |
| **MobileViT-XS** | ~1.1M | ✅ Yes | Extra small variant. |

**Best overall:** MobileNetV3-Small (2.5M) or EfficientNet-B0 (5.3M)
**Best for MCU:** ShuffleNetV2-x0.5 (1.3M) or LeNet (0.6M)

---

## 6. Object Detection

| Model | Parameters | On-Device? | Notes |
|-------|-----------|------------|-------|
| **YOLOv8n** | ~3.2M | ✅ Yes | Fastest YOLO, COCO mAP 37.3%. |
| **YOLOv9-Tiny** | ~2.1M | ✅ Yes | Very fast, good accuracy. |
| **YOLOv10n** | ~2.7M | ✅ Yes | Elimination-based real-time detection. |
| **YOLOX-Nano** | ~1M | ✅ Yes | Anchor-free, very small. |
| **RT-DETR-R18** | ~21M | ✅ Yes | Real-time DEtection TRansformer. |
| **SSD MobileNetV2** | ~5M | ✅ Yes | Single-shot detector, classic. |
| **Faster R-CNN MobileNet** | ~40M | ⚠️ Limited | Slower but more accurate. |
| **YOLO-NAS-Small** | ~22M | ✅ Yes | NAS-designed, good accuracy. |
| **NanoDet** | ~2M | ✅ Yes | Ultra-lightweight, no anchor. |
| **BlazeFace** | ~0.5M | ✅ Yes | Google, face detection only, extremely fast. |

**Best overall:** YOLOv8n (3.2M)
**Best for face detection:** BlazeFace (0.5M)
**Best for MCU:** YOLOX-Nano (1M) or NanoDet (2M)

---

## 7. Pose Estimation / Keypoint Detection

| Model | Parameters | On-Device? | Notes |
|-------|-----------|------------|-------|
| **MoveNet (SinglePose)** | ~6M | ✅ Yes | Google, single person, real-time. |
| **MoveNet (MultiPose)** | ~20M | ✅ Yes | Multi-person pose estimation. |
| **YOLO-Pose** | ~3.2M | ✅ Yes | Based on YOLOv8n, 17 keypoints. |
| **HRNet-W18** | ~18M | ✅ Yes | High-resolution, accurate. |
| **SimpleBaseline** | ~35M | ⚠️ Limited | Good accuracy, needs quantization. |
| **AlphaPose (small)** | ~30M | ⚠️ Limited | Multi-person, slower. |

**Best for single person:** MoveNet SinglePose (6M)
**Best for multi-person:** MoveNet MultiPose (20M)

---

## 8. Face Recognition

| Model | Parameters | On-Device? | Notes |
|-------|-----------|------------|-------|
| **ArcFace (MobileFaceNet)** | ~0.8M | ✅ Yes | 1.2M params, SOTA accuracy/size. |
| **FaceNet (Inception-ResNet-v1)** | ~5.5M | ✅ Yes | Google, well-known, good accuracy. |
| **FaceNet (Inception-ResNet-v2)** | ~23M | ✅ Yes | Better accuracy, still edge-friendly. |
| **CosFace (MobileFaceNet)** | ~0.8M | ✅ Yes | Similar to ArcFace, competitive. |
| **GhostFaceNet** | ~1.5M | ✅ Yes | Ghost modules for efficiency. |
| **BlazeFace** | ~0.5M | ✅ Yes | Face detection (not recognition). |
| **SCFace** | ~0.5M | ✅ Yes | Ultra-lightweight, low accuracy. |

**Best accuracy/size:** ArcFace with MobileFaceNet (0.8M)
**Best overall:** FaceNet Inception-ResNet-v1 (5.5M)

---

## 9. Translation

| Model | Parameters | On-Device? | Notes |
|-------|-----------|------------|-------|
| **mBART (base)** | ~610M | ✅ Yes | 50+ languages, fair quality. |
| **mBART (large)** | ~2.2B | ❌ No | Too large. |
| **NLLB-200-distilled-600M** | 600M | ✅ Yes | Facebook, 200 languages, excellent. |
| **T5-Small** | ~250M | ✅ Yes | 12 languages, decent. |
| **T5-Base** | ~220M | ✅ Yes | Similar to T5-Small. |
| **FasterTransformer Tiny** | ~100M | ✅ Yes | Optimized inference. |
| **BART (base)** | ~400M | ✅ Yes | 16 languages, good for NMT. |

**Best multilingual:** NLLB-200-distilled-600M (600M, 200 languages)
**Best balance:** mBART base (610M, 50+ languages)

---

## 10. Audio Generation / Music

| Model | Parameters | On-Device? | Notes |
|-------|-----------|------------|-------|
| **MusicGen (small)** | ~300M | ⚠️ Limited | Meta, text-to-music. Needs ~1GB RAM. |
| **EnCodec (small)** | ~10M | ✅ Yes | Audio tokenizer, not generative. |
| **Jukebox (tiny)** | ~500M | ⚠️ Limited | OpenAI, music generation. Slow. |
| **DDSP (small)** | ~1M | ✅ Yes | Differentiable DSP, instrument synthesis. |
| **SoundStream (small)** | ~5M | ✅ Yes | Audio compression/codec. |

**Best for music:** MusicGen small (300M) — needs quantization for edge
**Best for simple audio:** DDSP (1M)

---

## 11. Image Generation

| Model | Parameters | On-Device? | Notes |
|-------|-----------|------------|-------|
| **Stable Diffusion 1.5 (quantized)** | ~860M | ⚠️ Limited | Needs int4, ~1.5GB RAM. Slow on CPU. |
| **Stable Diffusion XL Turbo** | ~3B | ❌ No | Too large. |
| **LCM-LoRA** | ~100M | ✅ Yes | LoRA adapter for fast SD inference. |
| **PixArt-α Sigma** | ~670M | ⚠️ Limited | Fast, good quality. Needs quantization. |
| **FLUX.1-schnell (quantized)** | ~12B | ❌ No | Way too large. |
| **MiniDiffusion** | ~10M | ✅ Yes | Very small, low quality. Educational. |
| **DALL-E 2 (tiny)** | ~3B | ❌ No | Too large. |

**Best possible on edge:** Stable Diffusion 1.5 quantized to int4 (~860M)
**Best for MCU:** MiniDiffusion (10M) — very basic

---

## 12. Embedding Models

| Model | Parameters | Dimensions | On-Device? | Notes |
|-------|-----------|-----------|------------|-------|
| **all-MiniLM-L6-v2** | ~22M | 384 | ✅ Yes | Best small embedding, SentenceTransformers. |
| **all-MiniLM-L12-v2** | ~33M | 384 | ✅ Yes | Better accuracy, still fast. |
| **bge-small-en-v1.5** | ~33M | 512 | ✅ Yes | BAAI, strong multilingual. |
| **bge-base-en-v1.5** | ~110M | 768 | ✅ Yes | Better but larger. |
| **E5-small-v2** | ~33M | 384 | ✅ Yes | Microsoft, good for retrieval. |
| **GTE-small** | ~33M | 384 | ✅ Yes | Alibaba, strong retrieval. |
| **sentence-t5-small** | ~137M | 512 | ✅ Yes | T5-based, good quality. |
| **paraphrase-MiniLM** | ~22M | 384 | ✅ Yes | Similar to MiniLM-L6. |
| **Roberta-base** | ~110M | 768 | ✅ Yes | General-purpose embeddings. |

**Best overall:** all-MiniLM-L6-v2 (22M)
**Best multilingual:** bge-small-en-v1.5 (33M)

---

## 13. Keyword Spotting / Voice Commands

| Model | Parameters | On-Device? | Notes |
|-------|-----------|------------|-------|
| **TinyML Keyword Spotting** | ~10K–100K | ✅ Yes | TensorFlow Lite, runs on any MCU. |
| **YAMNet** | ~6M | ✅ Yes | Google, audio event classification. |
| **PANNs (small)** | ~5M | ✅ Yes | Audio neural networks, 527 classes. |
| **Vosk (keyword mode)** | ~5M | ✅ Yes | Offline keyword spotting. |

**Best for MCU:** TinyML KWS (~10K params)
**Best audio events:** YAMNet (6M)

---

## 14. Document Processing

| Model | Parameters | On-Device? | Notes |
|-------|-----------|------------|-------|
| **LayoutLMv3-base** | ~130M | ✅ Yes | Document understanding, layout + text. |
| **Donut-base** | ~100M | ✅ Yes | OCR-free document understanding. |
| **Surya Line/Word** | ~50M | ✅ Yes | Line/word level detection. |
| **DocLayNet (small)** | ~30M | ✅ Yes | Document layout analysis. |

**Best document understanding:** LayoutLMv3-base (130M)
**Best OCR-free:** Donut-base (100M)

---

## 15. Anomaly Detection / Time Series

| Model | Parameters | On-Device? | Notes |
|-------|-----------|------------|-------|
| **LSTM-based Anomaly** | ~1M | ✅ Yes | Simple, effective for time series. |
| **Autoencoder (small)** | ~50K | ✅ Yes | Very lightweight, unsupervised. |
| **TFT (tiny)** | ~1M | ✅ Yes | Temporal Fusion Transformer, small. |
| **N-BEATS (small)** | ~100K | ✅ Yes | Interpretable time series forecasting. |

**Best for IoT:** LSTM anomaly detection (~1M)
**Best forecasting:** N-BEATS small (~100K)

---

## Deployment Frameworks & Runtimes

| Runtime | Platforms | Best For |
|---------|-----------|----------|
| **ONNX Runtime** | All | Universal, best CPU performance |
| **TensorFlow Lite** | Android, iOS, MCU | Mobile and microcontroller |
| **PyTorch Mobile** | Android, iOS | PyTorch-native models |
| **CoreML** | iOS, macOS | Apple devices |
| **Apple MLX** | Apple Silicon | Mac, iPhone, iPad (your platform) |
| **OpenVINO** | Intel, ARM | x86 and ARM CPUs |
| **Google LiteRT** | Android, Raspberry Pi | Google-optimized inference |
| **TFLite Micro** | MCU, ESP32, STM32 | Microcontrollers |
| **WebNN** | Browsers | Web-based AI |
| **NCNN** | Mobile, embedded | Tencent, very fast on mobile |
| **MNN** | Mobile, embedded | Alibaba, cross-platform |
| **Baidu Paddle Lite** | Mobile, embedded | PaddlePorch ecosystem |

---

## Hardware Recommendations

| Device | Best Models | RAM Required |
|--------|------------|-------------|
| **ESP32-S3** | TinyML KWS, LeNet, BlazeFace | 512KB–2MB |
| **Raspberry Pi Zero 2W** | Whisper Tiny, MobileNetV3, YOLOv8n | 512MB–1GB |
| **Raspberry Pi 4 (4GB)** | Whisper Small, YOLOv8, Gemma 270M | 1–2GB |
| **Raspberry Pi 5 (8GB)** | Gemma 1B, Whisper Small, SD 1.5 (int4) | 2–4GB |
| **iPhone (A15+)** | All CoreML models, Kokoro, Whisper | 4–8GB |
| **Mac (M-series)** | All MLX models, Gemma 1B, SD 1.5 | 8–16GB |
| **Jetson Nano** | YOLOv8, Whisper Small, MobileNetV3 | 4GB |
| **Rockchip RK3588** | YOLOv8, Whisper Tiny, MobileNetV3 | 4–8GB (NPU accel) |

---

## Key Findings

1. **TTS is the most mature category** — Kokoro (150M) and Piper (15M) run beautifully on any CPU
2. **OCR is dominated by PaddleOCR** — PP-OCRv4 at ~25M total params is the sweet spot
3. **Speech recognition has excellent edge options** — Moonshine (27M) and Vosk (50M) are Whisper alternatives
4. **SLMs under 1B are now production-ready** — Gemma 3n 270M and Qwen2.5-0.5B are the leaders
5. **Image generation on edge is possible but slow** — SD 1.5 quantized to int4 (~860M) is the ceiling
6. **Embedding models are tiny and effective** — MiniLM-L6 (22M) is the gold standard
7. **Object detection is very efficient** — YOLOv8n (3.2M) runs at 30+ FPS on Raspberry Pi 4

---

## References

1. [Empowering Edge Intelligence: A Comprehensive Survey on On-Device AI Models](https://arxiv.org/html/2503.06027v1) — arXiv 2025
2. [On-Device Language Models: A Comprehensive Review](https://arxiv.org/html/2409.00088v1) — arXiv 2024
3. [From TinyML to Tiny Language Models: the State of Edge AI in 2026](https://derekmolloy.ie/from-tinyml-to-tiny-language-models-the-state-of-edge-ai-in-2026/) — Derek Molloy, 2026
4. [Transitioning from TinyML to Edge GenAI: A Review](https://www.preprints.org/frontend/manuscript/4ea38f4a78351995ea476f00f7d6b174/download_pub) — STMicroelectronics, 2025
5. [Best open-source speech-to-text models in 2026](https://www.gladia.io/blog/best-open-source-speech-to-text-models) — Gladia
6. [Best open source STT model in 2026 (with benchmarks)](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks) — Northflank
7. [The Best Open-Source Small Language Models (SLMs) in 2026](https://www.bentoml.com/blog/the-best-open-source-small-language-models) — BentoML
8. [Mastering Edge AI on Raspberry Pi with LiteRT and Gemma](https://developers.googleblog.com/mastering-edge-ai-on-raspberry-pi-with-litert-and-gemma/) — Google Developers, Aug 2026
9. [On-device small language models with multimodality, RAG, and Function Calling](https://developers.googleblog.com/google-ai-edge-small-language-models-multimodality-rag-function-calling/) — Google Developers, May 2025
10. [Awesome TTS & Voice Generation Models](https://github.com/wildminder/awesome-ai-voice) — GitHub
11. [Megrez-Omni Technical Report](https://arxiv.org/html/2502.15803v1) — arXiv 2025
12. [Mobile Foundation Model as Firmware (M4)](https://www.caidongqi.com/pdf/MobiCom24-M4.pdf) — MobiCom 2024
13. [Tiny-Align: Bridging ASR and LLM on Edge](https://arxiv.org/html/2411.13766v3) — arXiv 2024
14. [Real-Time Speech-to-Text on Edge](https://www.mdpi.com/2078-2489/16/8/685) — Information 2025
15. [Small Language Models and On-device AI Guide](https://techjacksolutions.com/ai-knowledge-hub/small-language-models/) — TechJack Solutions
