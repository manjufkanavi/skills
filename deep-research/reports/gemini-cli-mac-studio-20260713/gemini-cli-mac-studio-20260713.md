# Gemini CLI on Mac Studio — Comprehensive Research Report

**Date:** July 13, 2026
**Platform:** macOS (26.5.1) — Mac Studio M4
**API Key:** GEMINI_API_KEY set in ~/.bash_profile (53 chars)
**SDK:** google-genai v2.11.0 (via uv pip install)

---

## Executive Summary

Google's Gemini API provides a comprehensive AI platform accessible via Python SDK (`google-genai`). Unlike a traditional CLI tool, Gemini operates as an API-first platform with the Python SDK serving as the primary interface. This report covers installation, all available models (text, image, video, audio, embedding), API capabilities, and how to build a skill to harness Gemini's full capabilities on a Mac Studio M4.

---

## 1. Installation & Setup

### 1.1 Python SDK Installation

```bash
uv pip install google-genai
# Result: google-genai==2.11.0
```

Previously installed `google-generativeai` v0.8.5/0.8.6 (deprecated — Google recommends migrating to `google-genai`).

### 1.2 API Key Configuration

```bash
# ~/.bash_profile
export GEMINI_API_KEY="AQ.Ab8RN6JuyrLB[28chars]1l4p-wqX-Q"
```

Key length: 53 characters. Source of truth is `~/.bash_profile` — reading directly from the file bypasses platform truncation issues.

### 1.3 Client Initialization

```python
import google.genai as genai

client = genai.Client(api_key="YOUR_KEY")
```

The `Client` object is the entry point for all API operations.

---

## 2. Available Models

### 2.1 Text Generation Models

| Model | Description | Best Use Case |
|-------|-------------|---------------|
| `gemini-2.0-flash` | Fast, efficient general-purpose | Everyday tasks, code, chat |
| `gemini-2.5-flash` | Next-gen flash — faster, cheaper | High-throughput applications |
| `gemini-2.5-pro` | Most capable reasoning | Complex analysis, coding |
| `gemini-3.1-pro-preview` | Preview — cutting-edge reasoning | Research, deep analysis |
| `gemini-3.5-flash` | Latest flash preview | Future-proof fast responses |
| `gemini-flash-latest` | Auto-updates to newest flash | Always current |
| `gemini-pro-latest` | Auto-updates to newest pro | Always current |
| `gemini-2.0-flash-lite` | Lightweight, lowest latency | Simple queries, bulk processing |

### 2.2 Image Generation (Imagen 4.0)

| Model | Description |
|-------|-------------|
| `imagen-4.0-generate-001` | Standard image generation |
| `imagen-4.0-ultra-generate-001` | Highest quality images |
| `imagen-4.0-fast-generate-001` | Faster, lower quality |

### 2.3 Video Generation (Veo 3.1)

| Model | Description |
|-------|-------------|
| `veo-3.1-generate-preview` | Full-featured video generation |
| `veo-3.1-fast-generate-preview` | Faster video generation |
| `veo-3.1-lite-generate-preview` | Lightweight, shorter videos |

### 2.4 Audio Models

| Model | Description |
|-------|-------------|
| `gemini-2.5-flash-native-audio-latest` | Native audio input/output |
| `gemini-2.5-flash-native-audio-preview-09-2025` | Audio preview (Sep 2025) |
| `gemini-2.5-flash-native-audio-preview-12-2025` | Audio preview (Dec 2025) |
| `lyria-3-clip-preview` | Audio clip generation |
| `lyria-3-pro-preview` | Pro audio generation |

### 2.5 Embedding Models

| Model | Description |
|-------|-------------|
| `gemini-embedding-001` | Production text embeddings |
| `gemini-embedding-2` | Latest embeddings |
| `gemini-embedding-2-preview` | Preview embeddings |

### 2.6 Specialty / Preview Models

| Model | Description |
|-------|-------------|
| `gemini-3.1-flash-live-preview` | Live interactive mode |
| `gemini-3.5-live-translate-preview` | Real-time translation |
| `gemini-2.5-computer-use-preview-10-2025` | Computer use (GUI automation) |
| `deep-research-max-preview-04-2026` | Deep research (max depth) |
| `deep-research-preview-04-2026` | Deep research (standard) |
| `deep-research-pro-preview-12-2025` | Deep research (pro depth) |
| `gemini-robotics-er-1.5-preview` | Robotics control preview |
| `gemini-robotics-er-1.6-preview` | Robotics control preview v2 |

---

## 3. API Capabilities

### 3.1 Text Generation

```python
# Simple generation
resp = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Write 3 sentences about a Kannada poem on family unity"
)
print(resp.text)

# With generation config
from google.genai import types

resp = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="Explain gemini CLI capabilities",
    config=types.GenerationConfig(
        temperature=0.7,
        max_output_tokens=2048,
        response_mime_type="text/plain",
    )
)
```

### 3.2 Streaming

```python
# Streaming response for real-time output
for chunk in client.models.generate_content_stream(
    model="gemini-2.0-flash",
    contents="List 5 famous Kannada poets and their contributions"
):
    if chunk.candidates:
        for part in chunk.candidates[0].content.parts:
            if part.text:
                print(part.text, end="")
```

### 3.3 Multi-turn Chat

```python
# Create chat session
chat = client.chats.create(model="gemini-2.5-flash")

# Send messages
resp = chat.send_message("What is a vachana?")
print(resp.text)

# Chat maintains history automatically
resp = chat.send_message("Can you write one in Kannada?")
print(resp.text)
```

### 3.4 File Upload & Analysis

```python
# Upload any file type
file = client.files.upload(file="/path/to/document.pdf")
print(f"Uploaded: {file.uri} ({file.mime_type})")

# Analyze with Gemini
resp = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[
        "Analyze this document and summarize its key points",
        {"file_data": {"file_uri": file.uri, "mime_type": file.mime_type}}
    ]
)
```

**Supported file types:** PDF, DOCX, PPTX, XLSX, TXT, CSV, JSON, XML, HTML, audio (MP3, WAV, OGG, FLAC), video (MP4, AVI, MOV), images (PNG, JPEG, GIF, WEBP).

### 3.5 Token Counting

```python
count = client.models.count_tokens(
    model="gemini-2.0-flash",
    contents="Hello, world! This is a test."
)
print(f"Total tokens: {count.total_tokens}")
print(f"Input tokens: {count.input_tokens}")
```

### 3.6 Embeddings

```python
embedding = client.embeddings.get(
    model="gemini-embedding-001",
    content="Kannada poetry is a rich literary tradition"
)
print(f"Embedding dimensions: {len(embedding.values)}")
```

### 3.7 Image Generation

```python
from google.genai import types

# Generate image using Imagen 4.0
resp = client.models.generate_content(
    model="imagen-4.0-generate-001",
    contents="A minimalist illustration of an old woman in traditional Indian attire"
)
# Returns image data or URL depending on model
```

### 3.8 Video Generation

```python
# Generate video using Veo 3.1
resp = client.models.generate_content(
    model="veo-3.1-generate-preview",
    contents="A serene Kerala backwaters scene at sunset, cinematic"
)
# Returns video data or download URL
```

### 3.9 Audio Processing

```python
# Upload and transcribe audio
file = client.files.upload(file="/path/to/audio.mp3")
resp = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=["Transcribe this audio", {"file_data": {"file_uri": file.uri, "mime_type": "audio/mpeg"}}]
)
```

### 3.10 Web Search (Grounding)

```python
resp = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="What are the latest developments in AI?",
    config=types.GenerationConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
)
```

### 3.11 Function Calling

```python
def get_weather(city: str) -> str:
    