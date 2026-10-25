---
name: android-compose-debug
category: mobile
description: Fix Android Compose compile errors and rebuild the APK.
version: 1.3.0
author: Hermes Agent
tags: [android, compose, kotlin, build, assemble-debug]
license: MIT
created: 2026-10-13
updated: 2026-10-22
---

# Android Compose Build & Debug (Source Level)

Fix Kotlin/Jetpack Compose **compile errors** in an Android app and rebuild a debug APK. Distinct from `app-screenshot-capture`, which drives a *running* app; this works on the *source code before it compiles*.

## When to Use
Use when asked to fix build/compile errors, rebuild an Android Compose app after edits, or produce a debug APK. Covers Kotlin type mismatches, missing/merged imports, overload ambiguities, and Compose state-handling bugs. Also AGP configuration failures (e.g., a hollow application module missing its manifest breaking an apparently-unrelated root-level task), Room seeded-asset identity-hash mismatches, and verifying what actually shipped inside a built APK.

## When NOT This Skill
- Driving a running app to capture screens / fix runtime navigation → `app-screenshot-capture`.
- Automated E2E test suites for a website → `playwright-e2e`.

## Procedure
1. **Compile-check first, don't assemble blindly.** Run `compileDebugKotlin` (cheap) before `assembleDebug`. It returns every Kotlin error quickly; assemble only packages what already compiles.
   - Set the JDK this repo pins before Gradle (exact path is in memory; verify rather than assume): e.g. `export JAVA_HOME=/opt/homebrew/opt/openjdk@17` — a newer JDK (e.g. 26) breaks this repo's AGP/Gradle pair.
2. **Read the error list, group by file.** Count `^e:` lines per file and read each message's column to see which symbol is flagged. One bad type inference cascades into many unrelated-looking errors downstream — fix the declaration, not every cascade.
3. **Fix imports first.** Missing or merged `import` lines cause the widest error waves. After any import edit, verify no line contains two symbols (e.g. `import A` concatenated with the next import) — split joined lines, then rebuild before touching logic.
4. **Fix state/logic bugs.** See `references/compose-state-patterns.md` for the two recurring Compose state traps.
5. **Rebuild and re-check.** Re-run `compileDebugKotlin` until clean, then run `assembleDebug`. Locate the APK at `app/build/outputs/apk/debug/app-debug.apk`.

## Pitfalls (always-on rules)
- **Check compile before assembling.** `compileDebugKotlin` returns all Kotlin errors fast; a full `assembleDebug` is slower and surfaces the same errors later. Verify clean on compile first — assemble only packages what already compiles.
- **Fix the root cause, not every cascade.** One bad type inference (e.g. a map whose static type doesn't match) makes dozens of downstream lines fail with unrelated-looking errors (wrong return types, "val cannot be reassigned"). Fix the declaration; most cascade errors disappear on their own.
- **Verify imports after editing.** When inserting or bulk-editing `import` lines, a missing trailing newline concatenates two imports onto one line (`import A\nimport B` → `import Aimport B`). Kotlin treats that as a parse error and cascades. After any import edit, grep for lines holding two symbols and split them before rebuilding.
- **Nested standalone Gradle builds: run the wrapper that owns the files.** Some repos contain a second, independent Gradle project nested inside (its own `gradlew` + `local.properties`, e.g. a demo app under a multi-module root). Run `./gradlew` from that subproject's directory, not the repo root — the root wrapper builds the *other* app's `:app` and packages a different APK. Resolve `app/build/outputs/apk/debug/app-debug.apk` relative to the subproject you built in.
- **A hollow *application* module breaks every root-level task.** In a multi-module build, an included application module missing `src/main/AndroidManifest.xml` fails `ProcessApplicationManifest` even for tasks that seem unrelated — root-level tasks like `testDebugUnitTest` fan out to every project in `settings.gradle.kts`. AGP requires a manifest on application modules but library modules may omit one (AGP 8+). Fix with a minimal `<manifest />`; never delete that manifest when pruning.
- **Verify the shipped artifact, not just the build.** For content-bundled apps (Room seeded asset, raw resources), confirm the bytes actually made it into the package — unzip the APK and query/inspect the extracted copy — before claiming it ships.
- **Launch-crash reports: diff the version pair, then stop and ask.** When a newer build crashes on launch (in the field) while the previous one worked: sha256 the delivered copy against the build output, diff `unzip -l` listings, and diff the dex class lists between the two versions — R8 shrink is monotone, so a strict superset is structurally sound (recipe + the dexdump output-format trap: `references/build-gotchas.md`). If the artifact proves sound and the exact bytes run clean on a stock emulator in the user's saved state, the failure is device-specific (OEM/Android-version) — ask the owner for a real stack trace (crash dialog "More info" or `adb logcat -d | grep -A 40 FATAL`); never re-ship the same bytes as a "new APK" and call it fixed.

- **Platform stubs move between SDK versions — check nesting AND API level before assuming a TTS (or any framework) call resolves.** Against the API 34 stub, `android.speech.tts.Voice` is a *top-level* class (API 21+); the nested `TextToSpeech.Voice` / `TextToSpeech.Language` no longer resolve (Kotlin: "Unresolved reference 'Voice'/'Language'", with cascades on `.name`/`.locale`). Use top-level `Voice` (`name`, `locale`) + `isLanguageAvailable(Locale)` for download state. And `TextToSpeech.setVoice(Voice)` is **API 31+** — with minSdk < 31 it must be guarded (`Build.VERSION.SDK_INT >= S`, else fall back to `setLanguage`), or pre-Android-12 devices crash at runtime even though the build is green. The same check applies to any new platform API: javap the stub for nesting, then compare the method's min API against minSdk.
- **Kotlin numeric types are strict in ways prototype languages are not.** `float == int` is a compile error ("Operator '==' cannot be applied to 'kotlin.Float' and 'kotlin.Int'") — convert explicitly (`.toFloat()`); `roundToInt()` needs `import kotlin.math.roundToInt`. Logic that "obviously" works in a Python/JS mirror of the same computation (e.g. an integer-equality check on a float) still fails in Kotlin — expect type-mismatch + missing-import errors when porting validated logic across.

See `references/compose-state-patterns.md` for the map-delegate, parameter-shadowing, and continuous-control commit traps. See `references/build-gotchas.md` for the Room seeded-asset identity hash (id=42, KSP hash location), the hollow-module rule, the APK-asset verification recipe, the version-pair diff (sha256 / listing / dex) for launch-crash triage, and incremental-build zero-padding forensics (APK doubles while the entry list stays identical).
