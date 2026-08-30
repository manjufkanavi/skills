---
name: kokoro-tts-production
description: "Synthesize speech audio from any text using the live public Kokoro TTS API (kokoro.iacgenie.com) with a bearer key. Handles all voice languages and tuning options."
tags: [tts, audio, kokoro, text-to-speech]
related_skills: [kokoro-tts, voice-bridge]
---

# Kokoro TTS Production (Public API)

Generate speech audio from **any text** by calling the live public Kokoro TTS
endpoint at `https://kokoro.iacgenie.com` behind a Cloudflare Tunnel. This is the
**production/public** skill — distinct from `kokoro-tts`, which runs a local ONNX
model. This one uses the hosted engine, so no model files are needed locally and it
supports every voice language + tuning option the API offers.

## When to use

Use when a user wants audio generated from text and prefers the **hosted/production**
engine (or needs a language/voice not available in the local ONNX model). Examples:

- "Turn this text into speech / a voice note"
- "Generate audio for [text] in Italian/Japanese/Chinese/etc."
- Any one-off text-to-speech request where you want the full voice + tuning catalog

## Quick Start

```bash
# Simplest — default voice (af_heart), MP3, timestamped output in ~/voice-memos/
python3 ~/.hermes/skills/kokoro-tts-production/scripts/kokoro_tts.py "Hello world"

# Explicit voice + speed
python3 ~/.hermes/skills/kokoro-tts-production/scripts/kokoro_tts.py \
  "Buongiorno, come stai?" -v im_nicola -s 0.85

# List all voices (fetched live from the API)
python3 ~/.hermes/skills/kokoro-tts-production/scripts/kokoro_tts.py --list-voices

# Read text from stdin
echo "こんにちは世界。" | python3 ~/.hermes/skills/kokoro-tts-production/scripts/kokoro_tts.py -v jf_alpha
```

Every call fetches the API key from the homeserver over SSH (no secret stored in the
repo or on this machine) and posts to `https://kokoro.iacgenie.com/v1/audio/speech`.

## CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `text` | (stdin) | Text to synthesize (positional arg or stdin). UTF-8, any language. |
| `-o` / `--output` | timestamped MP3 in `~/voice-memos/` | Output file path. |
| `-v` / `--voice` | `af_heart` | Voice ID — run `--list-voices` for the full list. |
| `-s` / `--speed` | `1.0` | Speech rate (0.25–4.0). < 1 slower, > 1 faster. |
| `-m` / `--model` | `kokoro` | Model family: `tts-1`, `tts-1-hd`, or `kokoro`. |
| `-f` / `--format` | `mp3` | Output format: `mp3` or `wav`. |
| `-l` / `--list-voices` | — | Print all voices (fetched live) and exit. |

**Verified contract:** `/health` → 200 (no auth); `POST /v1/audio/speech` with a
valid key → HTTP 200 + valid audio (verified: ~11 KB MP3 for short text).

## Voice Languages & Tuning Reference

Kokoro-82M is multilingual. See `references/voices.md` for the full table. Quick
defaults:

| Language | Female voices | Male voices | Notes |
|----------|----------------|-------------|-------|
| American English | `af_heart`, `af_alloy`, `af_bella`, `af_jessica`, `af_kore`, `af_nicole`, `af_nova`, `af_river`, `af_sarah`, `af_sky` | `am_adam`, `am_michael`, `am_echo`, `am_eric`, `am_fenrir`, `am_liam`, `am_onyx` | Default voice: `af_heart` |
| British English | — | `bm_george` | Authoritative tone |
| Japanese | `jf_alpha` | `jm_kumo` | Use natural phrasing (no numbers) |
| Mandarin Chinese | `zf_xiaobei` | `zm_yunxi` | Pass CJK text directly |
| Italian | `if_sara` | `im_nicola` | Prefer slower speed 0.85–0.95 for natural delivery |
| Brazilian Portuguese | `pf_dora` | — | — |

**Tuning tips:**
- Speed **0.85–0.95** consistently sounds more human than 1.0 (clearer, natural pace).
- Punctuation controls pauses: commas and ellipses create short breaks; sentence
  breaks are longer. Write naturally for best results.
- Long text is segmented automatically at sentence boundaries (safety margin ~380 chars).

## How It Works

1. **Fetch key** — SSH to the homeserver (`mkanavi@192.168.0.116`, key
   `~/.ssh/home-server`) and read `/home/mkanavi/docker/kokoro/.api_key` (32 bytes).
   No secret is stored locally or in the repo.
2. **Synthesize** — POST JSON `{"model","input","voice","speed"}` to
   `https://kokoro.iacgenie.com/v1/audio/speech` with the `Authorization: Bearer <key>`
   header. The API returns raw audio (MP3/WAV).
3. **Segment** — for long text, the script splits into ≤ ~380-char segments and
   concatenates via `ffmpeg` (if available). Short text is a single call.
4. **Validate** — checks HTTP status; raises on 401/422/429 with a helpful message.

## Error Handling

| Symptom | Cause / Fix |
|---------|-------------|
| HTTP 401 | Key missing/invalid — SSH fetch failed or key revoked. Check connectivity to homeserver. |
| HTTP 422 | Invalid `voice` id — run `--list-voices` to pick a valid one. |
| HTTP 429 | Rate limit exceeded (burst > 20). Wait and retry. |
| HTTP 500 | Engine/model load error — retry; may be transient. |
| SSH timeout to homeserver | Increase `--ssh-timeout` (default 20s) or retry. |

## Configuration & Secrets

- **API key source:** `/home/mkanavi/docker/kokoro/.api_key` on the homeserver.
  Never committed, never stored locally — fetched over SSH at call time.
- **Public endpoint:** `https://kokoro.iacgenie.com` (dedicated Cloudflare Tunnel
  → nginx :80 → `kokoro-1:8881`). Host binds loopback-only; the tunnel provides
  public HTTPS. See `../iacgenie-platform/infra/homeserver/kokoro/USAGE.md` for
  deployment details.

## See Also

- **kokoro-tts** — Local Kokoro ONNX model (no network, offline). Use when you need
  fully local TTS or the specific Indian-voice presets.
- **voice-bridge** — Voice-to-voice conversation pipeline (STT + TTS + LLM).
- **iacgenie-platform/infra/homeserver/kokoro** — Deployment + API usage docs.
