---
metadata:
  hermes:
    tags: [android, apk, crash, adb, triage]
    related_skills: [android-compose-debug, app-screenshot-capture]
---

# Field crash triage — "installed but won't launch"

Owner reports the shipped APK will not open on their phone ("App keeps stopping"). Run the ladder in order; stop at the first real signal. The generic APK-diff forensics (sha256 / listing diff / dex class diff, incl. the dexdump output-format trap) live in the `android-compose-debug` skill — `references/build-gotchas.md` "Version-pair diff" section. This file is the app-specific wrapper: package names, prefs schema, version-transition reproduction.

Package: `com.example.awsredesign` (debug flavour adds `.debug`). Launch: `adb -s <serial> shell am start -n com.example.awsredesign.debug/com.example.awsredesign.MainActivity`.

## 1. Prove the delivered bytes
```bash
cd /Users/manjunathkanavi/aws-cloud-practitioner-trainer
shasum -a 256 aws-cloud-practitioner-trainer-v3-journey.apk app/build/outputs/apk/debug/app-debug.apk
```
Identical → the owner has exactly what you built; proceed. Different → rebuild + re-send first; everything else is premature.

## 2. Run the exact delivered bytes on the emulator
```bash
adb -s <serial> install -r aws-cloud-practitioner-trainer-v3-journey.apk
adb -s <serial> shell am force-stop com.example.awsredesign.debug
adb -s <serial> logcat -c
adb -s <serial> shell am start -n com.example.awsredesign.debug/com.example.awsredesign.MainActivity
sleep 6
adb -s <serial> logcat -d -b crash | head -40
adb -s <serial> shell dumpsys activity activities | grep topResumedActivity
```
"Launched" must mean a **resumed activity AND rendered pixels**: uiautomator dump (expect the screen's text) + a PIL scan for the expected palette colour (a saturated-primary fraction where the theme says). A resumed-but-blank screen is a failure, not a pass — the app can "open" into an empty composition.

## 3. Reproduce the owner's exact transition
The owner's phone = previous version + saved prefs, with the new APK installed over it.
```bash
git worktree add ~/.hermes/cache/scratch/<tag> <previous-version-commit>
cp local.properties <worktree>/        # untracked — a fresh worktree will NOT have it
(cd <worktree> && export JAVA_HOME=/opt/homebrew/opt/openjdk@17 && ./gradlew :app:assembleDebug)
adb -s <serial> install -r <prev-apk>
adb -s <serial> shell "run-as com.example.awsredesign.debug sh -c 'cat > shared_prefs/aws_trainer.xml'" < <state.xml>
adb -s <serial> install -r <new-apk>   # a TRUE upgrade, no uninstall — exactly what the owner did
```
then launch + logcat again. `install -r` without uninstall keeps state — that is the owner's real path (they download over the old). Build the previous version from git, never from memory of "what was in it". Pick a worktree path that does not already exist — leftover scratch dirs from earlier sessions collide and `git worktree add` fails.

Owner-state prefs (keys as written by `state/AppState.kt`): `<string>` first_name / last_name / theme_id (indigo|dark|forest|sunset|ocean) / best_scores (`id=score,…`), `<boolean>` sound_on, `<set name="completed_concepts"><string>id</string>…</set>`. Concept ids from `content/v2/course.json`. Write the file EXACTLY as Android writes it — the SKILL.md seeding pitfall covers the string-set shape that API 36 silently discards.

## 4. Structural diff old vs new
`unzip -l` listing diff and dex class-list diff, commed in BOTH directions (exact commands + the `Class descriptor  : '…'` colon-format trap + the monotonicity rule: `android-compose-debug` → `references/build-gotchas.md`). Interpretation:
- a file or a real class present in the old but missing in the new → R8 shrink regression → that IS the root cause; fix, rebuild, re-ship.
- only R8 synthetic `$$inlined$` artifacts gone and the new dex is a strict superset → structurally sound; sanity-check the added side is explainable (a new Compose component drags in a known dependency class batch, e.g. modal sheets bring gesture/drag classes).

## 5. All clean → it is the owner's device; do NOT re-ship the bytes
The stock AOSP emulator does not catch OEM-skin or Android-version-specific crashes (the owner's phone is a Samsung). Re-sending the same APK bytes as a "new APK" will crash identically — it is not a fix, and claiming otherwise burns trust. Ask for the trace, two routes:
- no computer: on the crash dialog tap **"More info"** (or long-press OK) → the error text appears; screenshot and send.
- USB: `adb logcat -c` → reproduce the tap → `adb logcat -d | grep -A 40 FATAL` → paste the output.
Also confirm install mode (upgrade over the old vs fresh after uninstall) — a corrupt/partial install masquerades as a launch crash; a full uninstall → fresh install is a zero-cost experiment worth asking for either way.

## After the fix
Apply the targeted fix for the exact cause, then re-run steps 1–3 on the new build and ship with pixel evidence. The "won't launch" class has no screenshot shortcut — the evidence IS that the app opens and renders on a real screen.
