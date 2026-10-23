# Android Offline TTS: Male & Female Voices — Research Report

**Topic:** How male/female voices are downloaded and used in Android offline TTS (Google "Speech Recognition & Synthesis" engine) — what a third-party app must do to offer an honest male/female voice selector.
**Method:** deep-research run of 2026-10-23 (91 unique pages, 75 queries, 3 rounds) + on-device verification against a 2025 Google TTS build on an S24 Ultra image (Android 16). Companion data: `data/raw/` and `data/synthesized/` for this slug; auto-generated slideshow: `android-offline-tts-male-and-female-voices--…-superpack-voice-data-20261023-183001.html`.

---

## 1. How offline voice data is downloaded

Offline voices in the Google TTS engine are **per-language voice-data packs** (historically "superpacks"), downloaded from *inside the engine's own settings UI* — never by a third-party app:

- The user-facing path is **Settings → System → Languages & input → Text-to-speech output → (engine gear icon) → Install voice data → pick a language → download** ([abilitynet guide](https://mcmw.abilitynet.org.uk/how-to-change-the-language-and-voice-used-for-text-to-speech-in-android-13), [RoadWhisper](https://roadwhisper.org/help-tts-voices/), [Android Authority](https://www.androidauthority.com/google-text-to-speech-engine-659528/)). Only the default/first voice per language ships pre-installed; every other language and the non-default voices of an installed language are downloadable.
- On-device (2025 build, `dumpsys package com.google.android.tts`): the **only** exported settings surface is the `INSTALL_TTS_DATA` action (`VoiceDataInstallActivity`). The older `com.google.android.tts.SETTINGS` action is gone from that build. A third-party app must therefore fire `INSTALL_TTS_DATA` first and fall back through legacy intents; on Android 11+ the app needs a `<queries>` block (package `com.google.android.tts` plus the intent actions) or `resolveActivity()` returns null and every fallback tier silently no-ops.
- Downloads require **Google Play Services** on the engine side; FOSS users cannot download voice data at all (the engine checks the Play Services signature — [HN discussion](https://news.ycombinator.com/item?id=29764295)). The common failure mode is the download arrow doing nothing ([XDA](https://xdaforums.com/t/help-google-tts-voice-data-why-cant-i-install-more-voice-data.4637)).
- Alternative offline engines for reference: Kaldi/sherpa-onnx model packs (piper voices), [VoxSherpa](https://github.com/CodeBySonu95/VoxSherpa-TTS), [sherpa-onnx TTS engine (F-Droid)](https://f-droid.org/en/packages/org.woheller69.ttsengine/), [Supertonic](https://speechcentral.net/2026-05-23/supertonic-tts-android-another-of). These sidestep Play Services entirely, at the cost of a separate engine app.

## 2. The core problem: the public API exposes no gender

`android.speech.tts.Voice` (verified against SDK 36: `getName()`, `getLocale()`, `getQuality()`, `getLatency()`, `getFeatures()`, `isNetworkConnectionRequired()`) carries **no gender, no varieties, no "is preinstalled" flag**. Practically every source in this research confirms the same wall:

- [App Inventor community](https://community.appinventor.mit.edu/t/texttospeech-how-set-male-female-voices-and-manage): "is there a way to select male or female voices, something more than pitch and speed?" — no public API answer.
- [Home Assistant community](https://community.home-assistant.io/t/google-tts-how-to-change-to-male-voice/8117) and [Pleco forums](http://www.plecoforums.com/threads/google-tts-voices.6770/) hit the identical wall for the same engine: voice lists are shown but unlabelled by gender, and selection "resets" to the default.
- Voice **names** are the only channel: legacy voices say it ("en-GB-female"), but the 2025 build's modern voices use opaque codes (`en-us-x-sfg-local`, `en-in-x-end-local`…) — which is exactly what organicmaps' [issue #12129](https://github.com/organicmaps/organicmaps/issues/12129) ("Implement proper TTS voice selection… doesn't support subvoice selection") documents as an open problem.

**Resolution found in this research:** the voice-code ↔ gender mapping exists in the community-curated [web-speech-recommended-voices](https://github.com/HadrienGardeur/web-speech-recommended-voices) project (now [Readium Speech](https://github.com/readium/speech), `json/en.json`), which documents: `x-sfg`/`x-tpc` (en-US) **female**, `x-ena`/`x-enc` (en-IN) **female**, `x-end`/`x-ene` (en-IN) **male**. Cross-checked against the on-device 473-voice list in this study: the installed modern voices match those codes, so a shipped app can map known codes → gender and match on *name substring*, while treating unknown/opaque names as "gender unknown" and never displaying a gender it cannot verify.

## 3. How engines actually pick a voice (and the substitution trap)

- `setLanguage(locale)` performs a **best-effort substitution** when the exact voice is absent — the engine returns `LANG_SUCCESS` while silently picking its default voice for that locale. The classic symptom (label says "Male British", you hear the female default) is this trap: the call succeeds, the voice differs.
- Setting the **locale variant** to a gender word (`Locale("en","GB","male")`) was tested on-device against the 2025 build: the engine *accepts* it but answers with the **same legacy default voice for every variant** — a dead end, not a selector.
- The reliable sequence is: `getVoices()` → filter by locale → match gender via the documented code map / name fragment / whole-word match (`"female"` *contains* the substring `"male"` — matches must be word-bounded) → `setVoice(voice)` → verify with an utterance. The engine honours `setVoice` with an installed voice (verified: distinct Synthesis requests per gender, full `start → done` callback).
- Timing pitfall: right after `onInit`, `getVoices()` can return **empty** (the engine's voice index is lazy — it is built on demand, which also explains the >10s first-call stalls seen in the wild). Robust code queries on a background thread, retries until the list settles, and treats "settled with zero voices" distinctly from "still loading".

## 4. Practical recipe for a third-party app

1. **Manifest:** `<queries>` with `<package android:name="com.google.android.tts"/>` + the intent actions (`com.google.android.tts.INSTALL_TTS_DATA`, legacy `com.google.android.tts.SETTINGS`, `android.intent.action.CALL_BUTTON`-style engine settings, market) so `resolveActivity` works on Android 11+.
2. **Voice list:** `getVoices()` on a background worker *after* `onInit`, with retry until non-empty or a settle timeout; cache per-app-session.
3. **Gender:** map known voice codes (Readium `en.json`) + `#gender`/word name matching; everything else = "unknown" → never label it.
4. **Download:** `INSTALL_TTS_DATA` → legacy `com.google.android.tts.SETTINGS` → `market://details?id=com.google.android.tts` → `https://play.google.com/store/apps/details?id=com.google.android.tts` → system TTS settings; first `resolveActivity()`-non-null wins.
5. **Honesty:** caption the reader with the *actual* voice (accent + gender only if verified); when the chosen gender has no installed voice for the accent, say so and point at the download — do not silently substitute and mislabel.
6. **Field triage:** keep a hidden self-test entry point and engine timing/utterance logs, because engine behaviour (lazy index, voice substitution, model load crashes) is invisible without them.

## 5. On-device verification (this study)

On the 2025 Google TTS build (Android 16, S24 Ultra image): 473 voices returned ~300 ms after the voice query was correctly started; en-US carries documented female (`x-sfg`/`x-tpc`) and male voices, en-IN carries documented male (`x-end`/`x-ene`) with the female pair not installed, en-GB returns opaque (`x-gba`) names; `INSTALL_TTS_DATA` resolves to the "Your languages / Available languages" screen (the only settings surface exported); male and female `setVoice` selections produce **distinct engine synthesis requests**, with a full `start → done` utterance for the female voice. One caveat: the engine's tflite inference thread can `SIGILL` on some models under swiftshader/emulated CPUs (emulator artifact; real devices unaffected in practice).

## Key sources

- [organicmaps issue #12129 — proper TTS voice selection](https://github.com/organicmaps/organicmaps/issues/12129) · [organicmaps TTS FAQ](https://organicmaps.app/faq/voice/text-to-speech-tts-and-voice-directions-on-android/)
- [Readium Speech / web-speech-recommended-voices](https://github.com/HadrienGardeur/web-speech-recommended-voices) (voice-code → gender/quality mapping)
- [Android TextToSpeech API reference](https://developer.android.com/reference/android/speech/tts/TextToSpeech) (no gender field on `Voice`)
- [Abilitynet — changing language & voice (Android 13)](https://mcmw.abilitynet.org.uk/how-to-change-the-language-and-voice-used-for-text-to-speech-in-android-13) · [RoadWhisper voice install help](https://roadwhisper.org/help-tts-voices/) · [Android Authority — modify Google TTS](https://www.androidauthority.com/google-text-to-speech-engine-659528/)
- [XDA — voice data won't install](https://xdaforums.com/t/help-google-tts-voice-data-why-cant-i-install-more-voice-data.4637) · [HN — Play Services requirement](https://news.ycombinator.com/item?id=29764295)
- [App Inventor — male/female selection wall](https://community.appinventor.mit.edu/t/texttospeech-how-set-male-female-voices-and-manage) · [Home Assistant — male voice wall](https://community.home-assistant.io/t/google-tts-how-to-change-to-male-voice/8117)
- Offline engine alternatives: [sherpa-onnx/F-Droid](https://f-droid.org/en/packages/org.woheller69.ttsengine/) · [VoxSherpa](https://github.com/CodeBySonu95/VoxSherpa-TTS) · [Supertonic on Android](https://speechcentral.net/2026-05-23/supertonic-tts-android-another-of)

*Auto-collected corpus (91 pages, incl. Gemini/Cloud TTS noise) retained under `data/raw/` and `data/synthesized/` for this topic.*
