# Sound system (ux-redesign app)

## Architecture (`theme/Sound.kt` — object `SoundFx`)
- Three packaged mp3s through one `SoundPool` (3 streams, STREAM_MUSIC): `res/raw/sparkle.mp3` (correct — three quick bell blips) and `res/raw/descent.mp3` (wrong — minor two-note drop) — the owner's picks from five candidates each — plus `res/raw/fanfare.mp3` (quiz/lesson complete — bright rising C-major arpeggio, the owner's pick of three candidates, v3.12). The old ToneGenerator beep fanfare is retired; `fanfare(context)` plays the mp3.
- Call sites: `ConceptScreen` question flow (correct/wrong per answer) and the last question's Continue→Finish (`fanfare(context)`). One sound covers quiz completion AND lesson completion — the last quiz round of a lesson IS the lesson completion, so there is no separate trigger. All gated by `AppState.soundOn` (Settings "Answer sounds").
- SoundPool needs a file path, so on first use each raw asset is copied once into `filesDir`, then `pool.load(path)`. Track the stream id from `play(...)` and stop it before the next answer sound (fast answer sequences otherwise overlap).

## Pitfalls
- **`SoundPool.loadResource(Context, resId, priority)` was removed in API 33.** With compileSdk >= 33 it is an unresolved reference at compile time. Use `load(path)` + the one-time raw-to-filesDir copy instead (SoundPool decodes MP3 from minSdk 26 up).
- **res/raw filenames must be lowercase** (no uppercase or dashes) or aapt2 fails the build.
- **numpy → mp3**: write a real WAV header via the stdlib `wave` module (`wave.open(path, 'wb')` + setnchannels/sampwidth/framerate/writeframes) — dumping raw PCM bytes with `Path.write_bytes` yields a file ffmpeg rejects ("Invalid data found"). When adding multi-segment bell/pluck arrays, give every segment the same sample length first (numpy won't broadcast different lengths).

## Owner pattern: audition candidates before wiring
When the owner dislikes the current sound, don't guess a replacement — present options and let them choose:
1. Synthesize 5 candidates per state (each ~0.2-0.5s) with numpy: sine/triangle/square + exponential-decay envelope + one-pole lowpass + 6-8ms fade in/out, normalize to 0.89 peak.
   - Good "correct" starting points: two-note bell, major arpeggio, pitch-rise glide, short round pop, three quick high blips.
   - Good "wrong" starting points: low square buzz, minor two-note drop, soft thud + noise, descending glide, double thud.
   - Good "success/completion" starting points: rising major arpeggio in bell timbre (~1.3s), soft major chord + high shimmer, playful pitch-rise pluck with grace note.
2. Encode with `ffmpeg -codec:a libmp3lame -qscale:a 4` and send all candidates as `MEDIA:` lines (Telegram plays mp3 inline so the owner can audition).
3. The owner replies with their picks (e.g. "success 1"); wire exactly those into res/raw (lowercase names like `fanfare.mp3`), rebuild, ship. Reuse the same candidate files — do not re-synthesize. Current owner picks (2026-10-21): sparkle, descent, and the fanfare arpeggio all live in res/raw.
