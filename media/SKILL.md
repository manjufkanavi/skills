---
name: media
description: >
  Media processing and search: GIF search, YouTube transcripts, audio generation,
  spectrograms, and video/image generation. Covers searching for media assets,
  processing YouTube content, and generating visual/audio media locally.
version: 1.0.0
author: Hermes Agent
tags: [media, gif, youtube, audio, video, image, generation, search]
---

# Media Processing & Generation

**Umbrella for media-related tools: GIF search, YouTube content, audio/song generation, spectrograms, and image/video generation.**

## Table of Contents

- [1. GIF Search](#1-gif-search)
- [2. YouTube Content](#2-youtube-content)
- [3. Audio & Music](#3-audio--music)
- [4. Image & Video Generation](#4-image--video-generation)

---

## 1. GIF Search

Search and download GIFs from Tenor API.

**Load when:** "search for a GIF", "find a reaction GIF", "search for memes"

**Setup:** Requires `TENOR_API_KEY` environment variable.

```bash
# Search GIFs
curl -s "https://tenor.googleapis.com/v2/search?q=thumbs+up&limit=5&key=${TENOR_API_KEY}" | jq -r '.results[].media_formats.gif.url'

# Get metadata
curl -s "https://tenor.googleapis.com/v2/search?q=cat&limit=3&key=${TENOR_API_KEY}" | jq '.results[] | {title: .title, url: .media_formats.gif.url}'
```

**See:** `references/gif-search.md` for full documentation.

---

## 2. YouTube Content

Process YouTube videos: extract transcripts, generate summaries, threads, and blog posts.

**Load when:** "summarize this YouTube video", "get transcript from YouTube"

**See:** `youtube-content` skill for full workflow.

---

## 3. Audio & Music

### AudioCraft (`audiocraft-audio-generation`)

Text-to-music and text-to-sound generation using MusicGen and AudioGen.

- **Load when:** "generate music from a description", "create a sound effect"

### HeartMuLa (`heartmula`)

Suno-like song generation from lyrics + tags.

- **Load when:** "write a song from these lyrics"

### Songwriting (`songwriting-and-ai-music`)

Songwriting craft and Suno AI music prompts.

- **Load when:** "help me write song lyrics", "create a Suno prompt"

### SongSee (`songsee`)

Audio spectrograms and feature extraction (mel, chroma, MFCC) via CLI.

- **Load when:** "analyze this audio file", "generate a spectrogram"

### Voice Bridge (`voice-bridge`)

Speech-to-speech voice communication pipeline: Telegram voice note → Whisper STT → LLM → Kokoro TTS → voice response.

- **Load when:** "voice to voice", "send me a voice reply", "voice conversation"
- **See also:** `voice-bridge` skill

---

## 4. Image & Video Generation

### ComfyUI (`comfyui`)

Generate images (Flux Dev) and videos (Wan 2.1 1.3B) via ComfyUI on Mac Studio M4.

- **Load when:** "generate an image", "create a video"

### Video Generator (`video-generator`)

AI video generation using Wan 2.1 via ComfyUI. Full lifecycle: install, model download, workflow execution.

- **Load when:** "generate a video from text"

### Video Edit (`video-editing`)

Script-based video editing using moviepy.

- **Load when:** "cut this video", "merge videos", "add text to video"

### GIF Search (`gif-search`)

Search/download GIFs from Tenor.

- **See:** Section 1 above

---

## Pitfalls

- **Tenor API key:** Always check `TENOR_API_KEY` is set before searching GIFs
- **ComfyUI:** Requires Mac Studio M4 with sufficient VRAM
- **Audio tools:** MusicGen and AudioGen require downloading models on first use (~1-2 GB)
