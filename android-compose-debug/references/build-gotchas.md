---
metadata:
  hermes:
    tags: [android, room, agp, ksp, apk]
    related_skills: []
---

# Android Build Gotchas (beyond Kotlin compile errors)

## Room seeded-asset identity hash (`createFromAsset`)

When a Room database ships as a pre-seeded asset (offline content DB), the asset must satisfy Room's identity validation or the app fails on open in debug builds ("Room cannot verify the data integrity").

- **Get the real hash from KSP output.** For Android modules, KSP emits **Java** — `ContentDatabase_Impl` is a `.java` file, not `.kt`. The current round lives at `<module>/build/kspCaches/{debug|release}/backups/java/byRounds/1/<package>/…_Impl.java`; `build/generated/ksp/` can hold stale copies. Search by class name, not by extension. The hash is in the generated `room_master_table` INSERT: `INSERT OR REPLACE INTO room_master_table (id,identity_hash) VALUES(42, '<hash>')`.
- **The `room_master_table` row must use `id = 42`.** Room 2.6.x `DBUtil.validateIdentityHash` queries `SELECT identity_hash FROM room_master_table WHERE id=42`. A hand-rolled seed with any other id (1, 0, …) fails validation even when the hash string is correct.
- **DDL must match `createAllTables` exactly** — column names/order, NOT NULL flags, PKs, index names. Copy the generated `db.execSQL` statements verbatim into the seed script.
- **After seeding, verify the shipped artifact**: `unzip -o -q app.apk assets/<db>` then `sqlite3` the extracted copy — check the `room_master_table` row, row counts, and a sample of content.

## Hollow application module

An application-type module included in `settings.gradle.kts` but with no `src/main/` sources (a planning-era scaffold) fails AGP's `ProcessApplicationManifest` input validation — and because root-level tasks fan out to all projects, it breaks *every* root task (`testDebugUnitTest`, `build`), even ones that never target that module.

- AGP requires `src/main/AndroidManifest.xml` on **application** modules; **library** modules may omit it (AGP 8+, `namespace` suffices).
- Diagnose: the error names the missing manifest file; check the module's `build.gradle.kts` for `com.android.application` vs `com.android.library`.
- Minimal fix: add `<manifest />` (namespace comes from the build file). If the module is truly dead, delete it from `settings.gradle.kts` instead — only with explicit approval.

## APK asset verification recipe

```bash
unzip -o -q app/build/outputs/apk/debug/app-debug.apk -d /tmp/apkcheck
sqlite3 /tmp/apkcheck/assets/content.db "SELECT id, identity_hash FROM room_master_table;"
```

For raw resources: `unzip -l app.apk | grep res/raw`. Run this before sending a content-bearing APK to the user.

## Version-pair diff — "shipped but won't launch" triage

When an older version ran on the user's device but the newer APK crashes on launch (and the new one runs clean on a stock emulator), diff the two APKs to prove or refute a shrink regression:

```bash
# file listing — anything present in the old and missing in the new is a real regression
unzip -l old.apk | awk '{print $4}' | sort -u > l1.txt
unzip -l new.apk | awk '{print $4}' | sort -u > l2.txt
comm -23 l1.txt l2.txt        # in old, missing from new

# dex classes — extract ALL dex files (multi-dex safe)
unzip -o -q old.apk 'classes*.dex' -d /tmp/apkold
unzip -o -q new.apk 'classes*.dex' -d /tmp/apknew
$SDK/build-tools/<latest>/dexdump /tmp/apkold/classes*.dex 2>/dev/null | grep -oE "Class descriptor  : 'L[^']+'" | sort -u > c_old.txt
$SDK/build-tools/<latest>/dexdump /tmp/apknew/classes*.dex 2>/dev/null | grep -oE "Class descriptor  : 'L[^']+'" | sort -u > c_new.txt
comm -23 c_old.txt c_new.txt  # classes removed (only R8 $$inlined$ synthetics are healthy)
comm -13 c_old.txt c_new.txt  # classes added (should be explainable: new component's dependency batch)
```

- **dexdump output-format trap:** the header line is `Class descriptor  : 'L...;'` — two spaces, then a colon. A grep pattern that omits the colon matches **zero lines silently**; a 0/0 diff means the pattern is wrong, not that the APKs are identical. Always sanity-check one known class name appears in the output before trusting the diff.
- **Monotonicity rule:** R8/shrink only removes classes that nothing references. If every old class still exists (or only `$$inlined$` synthetics changed) and no resources disappeared from the listing, the new APK cannot have lost functionality — the failure is environmental, not a build regression.
- **All clean + stock emulator clean ⇒ device-specific failure** (OEM skin or Android-version dependent; stock AOSP does not catch it). Do **not** re-ship the same bytes as a "fix" — it will crash identically. Ask the user for the actual trace: crash dialog **"More info"** (long-press OK) → screenshot, or `adb logcat -c` → reproduce → `adb logcat -d | grep -A 40 FATAL`. Also confirm install mode (upgrade over vs fresh after uninstall) — a corrupt partial install masquerades as a launch crash.

## Incremental-build zero padding (APK doubles, entry list stays identical)

AGP's incremental zip/dex step can corrupt the packaged file in a second way besides duplicate entries: a multi-MB **all-zero padding region** inside the zip (seen before the native `.so` entries / after classes.dex). Signature: on-disk size roughly doubles (e.g. 3.4→6.7 MB) while `unzip -l` shows the *same* entry count and per-entry sizes — the entry count check passes, only the file-size check catches it.

Diagnose with the central directory (the authoritative entry list — do **not** scan raw bytes for `PK\x03\x04` to find local headers: deflate streams can contain that 4-byte magic and report phantom entries, inflating the count):

```python
import zipfile
z = zipfile.ZipFile("app.apk")
prev_end = 0
for i in z.infolist():
    if i.header_offset - prev_end > 100_000:
        print("GAP", i.header_offset - prev_end, "bytes before", i.filename)
    prev_end = max(prev_end, i.header_offset + 30 + len(i.filename.encode()) + len(i.extra) + i.compress_size)
```

Fix: `./gradlew clean :app:assembleDebug` — a clean package is tight again (real content delta is usually tens of KB). Clean-before-ship is the prevention; the size sanity check is the detector; only if the *clean* build is still fat, diff the entries.

## TTS voice gender matching (on-device TextToSpeech)

`Voice` carries a name + locale but **no gender field** — Google's voices encode it in the name ("Google UK English Female/Male"). Match with a **whole-word** regex (`\bmale\b` / `\bfemale\b`, ignore case): `"female"` contains `"male"` *as a substring* (f-e-**m-a-l-e**), so a plain `name.contains("male")` silently selects the female voice first whenever both packs are installed — the gender switch appears dead. Also: voice packs are downloaded **per voice** (male and female of a locale are separate downloads) and `getVoices()` lists only installed voices, so a locale can be "downloaded" while one gender is absent — surface that in the UI (what will actually play) instead of silently playing the other gender.
