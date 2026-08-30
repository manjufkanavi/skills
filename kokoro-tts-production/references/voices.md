# Kokoro Voice & Tuning Reference (verified against https://kokoro.iacgenie.com)

## Full voice inventory (`GET /v1/voices`)

| Voice ID | Description (language) |
|----------|------------------------|
| `af_heart` | American female — warm, natural (**recommended default**) |
| `af_alloy` | American female — smooth |
| `af_aoede` | American female |
| `af_bella` | American female — expressive, energetic |
| `af_jessica` | American female — bright |
| `af_kore` | American female — clear, professional |
| `af_nicole` | American female — friendly |
| `af_nova` | American female — bright, youthful |
| `af_river` | American female — calm |
| `af_sarah` | American female — conversational, warm |
| `af_sky` | American female — neutral, versatile (default) |
| `am_adam` | American male — deep, rich |
| `am_michael` | American male — clear, neutral |
| `am_echo` | American male — soft, gentle |
| `am_eric` | American male — authoritative |
| `am_fenrir` | American male — distinctive, deep |
| `am_liam` | American male — warm, casual |
| `am_onyx` | American male — dark, resonant |
| `bm_george` | British male — authoritative, posh |
| `jf_alpha` | Japanese female — soft |
| `jm_kumo` | Japanese male — calm |
| `zf_xiaobei` | Mandarin Chinese female — light, cute |
| `zm_yunxi` | Mandarin Chinese male — clear |
| `if_sara` | Italian female — warm, expressive |
| `im_nicola` | **Italian male** (matches user preference) |
| `pf_dora` | Brazilian Portuguese female — warm |

**Total: 26 voices.** List them live with `python3 kokoro_tts.py --list-voices`.

## Tuning options (`POST /v1/audio/speech`)

| Field | Type | Range / values | Purpose |
|-------|------|----------------|---------|
| `model` | string | `tts-1`, `tts-1-hd`, `kokoro` | Model family. `kokoro` is the multilingual default for this deployment. |
| `input` | string | any text | Text to synthesize (UTF-8). Supports multiple languages. |
| `voice` | string | see table above | Voice ID; invalid → **422**. |
| `speed` | number | 0.25–4.0 (default ~1.0) | Speech rate multiplier (< 1 slower, > 1 faster). |

## Tuning by goal (verified defaults)

| Goal | Voice(s) | Speed | Text tip |
|------|----------|-------|----------|
| Natural, human-like (user preference) | `af_heart`, `im_nicola`, `if_sara` | 0.85–0.95 | Add commas / ellipses for pauses; write naturally |
| Clear, articulate narration | `af_bella`, `am_michael` | 0.9–1.0 | Short sentences, avoid run-ons |
| Indian-style accent (local model only) | `if_sara`, `im_nicola` | 0.85 | Natural phrasing, avoid complex numbers |
| Warm, friendly | `af_heart`, `am_liam` | 0.9–1.0 | Conversational tone, contractions fine |
| Authoritative / news | `am_adam`, `bm_george` | 0.95–1.0 | Slow pace, deliberate punctuation |
| Upbeat / energetic | `af_jessica`, `am_fenrir` | 1.05–1.2 | Short punchy sentences |

## Per-language examples (public API)

```bash
KEY="..." # fetched by the script automatically; not stored anywhere
BASE="https://kokoro.iacgenie.com"

# American English (default voice)
curl -s "$BASE/v1/audio/speech" -H "Authorization: Bearer $KEY" \
  -d '{"model":"kokoro","input":"Hello world.","voice":"af_heart"}'

# Italian — slower, more natural (user preference)
curl -s "$BASE/v1/audio/speech" -H "Authorization: Bearer $KEY" \
  -d '{"model":"kokoro","input":"Buongiorno, come stai?","voice":"im_nicola","speed":0.85}'

# British English
curl -s "$BASE/v1/audio/speech" -H "Authorization: Bearer $KEY" \
  -d '{"model":"kokoro","input":"A fine day, isn'"'"'t it?","voice":"bm_george"}'

# Mandarin Chinese
curl -s "$BASE/v1/audio/speech" -H "Authorization: Bearer $KEY" \
  -d '{"model":"kokoro","input":"你好，世界。","voice":"zf_xiaobei"}'

# Japanese
curl -s "$BASE/v1/audio/speech" -H "Authorization: Bearer $KEY" \
  -d '{"model":"kokoro","input":"こんにちは世界。","voice":"jf_alpha"}'

# Brazilian Portuguese
curl -s "$BASE/v1/audio/speech" -H "Authorization: Bearer $KEY" \
  -d '{"model":"kokoro","input":"Olá, mundo!","voice":"pf_dora"}'
```

## Notes

- `/health` (no auth) → `{"status":"ok","engine":"kokoro"}`.
- Rate limit: burst ~20 requests; exceeding → **429**. Wait and retry.
- Invalid `voice` → **422**; missing/invalid key → **401**.
- Speed `0.85–0.95` consistently sounds more human than 1.0 (clearer, natural pace).
