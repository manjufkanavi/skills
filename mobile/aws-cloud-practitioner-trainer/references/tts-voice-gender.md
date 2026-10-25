---
name: tts-voice-gender
description: Google TTS voice-gender catalog decode, key normalization, and verification for the reader's voice logic.
metadata:
  hermes:
    tags: [tts, android, voice-gender, protobuf]
    related_skills: [aws-cloud-practitioner-trainer]
---

# TTS voice-gender data — catalog decode, key normalization, verification

The durable fact set for the reader's voice logic. Everything here was established from the device (the learner's own engine build), not from the web.

## Authoritative source: the engine's signed catalog

Google TTS (2025 build, `/product/app/GoogleTTS/GoogleTTS.apk`) ships `assets/voices-list-dsig.pb` — the complete voice list, protobuf-encoded:

- top-level field 2 = one locale block { field 17 = canonical locale (e.g. `en_GB`), field 9 = alt locales }
- voice entry = field 37 { field 13 = voice name, field 19 = voice code, **field 16 = gender (1 = female, 2 = male)** }
- a block may carry voices via multiple nested field-23 groups AND direct field-37 entries — collect **both** (the first decode that kept only the last f23 group silently dropped en-US).

Walk the raw bytes with a minimal protobuf reader (varint fields, skip unknown, recurse into submessages; `adb pull` the apk → `unzip` the asset). 2025 build: **81 locale blocks, 314 distinct voice names**.

Do NOT seed the gender map from web voice databases (Readium Speech et al.): they carry only old-generation `-network` voice codes and miss the modern opaque local voices — a map built from them marks most locales "unknown", the resolver's first-in-locale fallback plays the engine default (females list first) = the reported gender swaps.

Anchor-verify any decode against known voices before trusting it: `en-gb-x-rjs` = male, `en-gb-x-gba` = female, `en-us-x-tpd` = male, `en-us-x-sfg` = female, `en-in-x-ena` = female.

## 2025 catalog — English facts

English is present in exactly: en-AU, en-GB, en-IN, en-NG, en-US. **No en-ZA.**

- en-GB: gba=f, gbb=m, gbc=f, gbd=m, gbg=f, gbh=m (+ rjs=m network)
- en-AU: aua=f, aub=m, auc=f, aud=m, amh=m
- en-US: sfg=f, tpc=f, tpd=m, tpf=f, iob=f, iol=m, iom=m
- en-IN: ena=f, enc=f, end=m, ene=m (the app's male default)

Bare voice codes do not collide across locales (checked) — but the map is keyed on the **normalized full name** anyway, which is collision-free by construction.

## Key normalization (the map lookup must survive engine naming)

Build `KNOWN_VOICE_GENDER` keys as: lowercase → if the name contains `#`, take the part after the last `#` → strip a trailing `-local`/`-network`/`-cloud` suffix.

Trap: `lower.substringAfter("#", "")` returns `""` when there is NO `#` — guard with `if ('#' in lower) … else lower`, or the whole map silently misses every real voice (first v3.23 build still played the wrong gender for this reason).

## Resolution contract (v3.23)

1. documented voice of the requested **gender** (wins over accent — the gender pick is the stronger learner intent);
2. another English reader accent's voice, in accent-list order (saves accents whose voice data the engine no longer ships, e.g. S. Africa);
3. any voice of the locale (gender unknown — caption it honestly);
4. any documented voice of the gender.

`applyReaderSettings` calls `setVoice` on the resolved engine voice (`getVoices()` entries are installed data) — never `setLanguage` when a voice resolves; request the locale only as the last resort. The `Locale("en","GB","male")` variant trick is a tested dead end on the 2025 engine (same default voice back).

## Verification (fastest first)

- `adb shell pm clear com.example.awsredesign.debug` — fresh-install state (defaults since v3.23.1: India / Male / 1×).
- `adb shell am start -n com.example.awsredesign.debug/com.example.awsredesign.MainActivity --ez awt_tts_selftest 1 --ez awt_tts_resolve_all 1` — logs the full accent×gender resolution matrix under tag `TtsSelftest` with no slow speaks; read it with `adb logcat -d -s TtsSelftest | grep -A20 "RESOLVE-ALL"`. Every row must show the requested gender in its caption.
- Drop the flags for the full self-test (utterance start/done/error, engine deaths, per-accent download status).
- Emulator caveat: audio synthesis of some models can SIGILL on the emulated CPU — the per-voice Synthesis log lines prove the SELECTION; confirm actual sound on the owner's phone.
- The settings UI (accent chips, "Voice: …" line) renders from `TtsAccents.ALL` + `AppState` — if the self-test matrix is right, the UI is right; when emulator taps stop registering, trust the matrix over the screen.
