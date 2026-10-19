---
name: sast-android-suite
description: Run the Android SAST suite and fix findings before commit.
tags: [sast, android, kotlin, security, lint, mobsfscan, narvy, semgrep, detekt, konsist]
version: 1.1.0
author: manjufkanavi
license: MIT
hermes:
  tags: [sast, android, security]
  related_skills: [sast-autofix]
---

# Android SAST Suite — Run + Auto-Fix

Run all locally-runnable SAST tools against this Android project's source, categorize findings into fixable vs false-positive, apply surgical fixes for real issues, and commit/push on the security branch. Run repeatedly until fixable findings reach zero.

## When to Use

Use when the user wants to run SAST security scans on this Android project and fix any real findings — i.e. "run all the linters", "scan for vulnerabilities", or "fix SAST findings". Covers mobsfscan, narvy-cli, semgrep (custom rules), detekt, Android Lint, and Konsist (architecture rules). Krit is not locatable here.

## Overview

Unlike iacgenie-platform (which runs SAST via GitHub Actions and reads artifacts), this Android project runs all tools **locally against the source checkout**. The suite: mobsfscan (mobile SAST), narvy-cli (local SAST), semgrep (custom offline rules), detekt (Kotlin analysis + baseline), Android Lint, and Konsist (architecture rules). Krit is not locatable in this sandbox — skip it.

## Prerequisites / Environment (CRITICAL)

- **JDK 17 for Gradle**: `export JAVA_HOME=/opt/homebrew/Cellar/openjdk@17/17.0.18/libexec/openjdk.jdk/Contents/Home`. The default `gradle` JAVA_HOME points to a newer openjdk (26), which Kotlin can't target → it falls back to JVM_23 and fails with "Inconsistent JVM-target compatibility (17 vs 23)".
- **No GNU `timeout` on macOS**: do NOT run `timeout 600 gradle ...`. The terminal tool's own `timeout` param handles it; a shell `timeout` command returns exit 127 (command not found).
- **mobsfscan venv**: `~/sectools/mobsfscan-venv` (dedicated, NOT in repo). Use `~/sectools/mobsfscan-venv/bin/<tool>`.

## Tool 1 — mobsfscan (mobile SAST, semgrep + libsast backend)

```bash
cd <repo> && ~/sectools/mobsfscan-venv/bin/mobsfscan --type android app/src/main > /tmp/mb.log 2>&1
# exit 0 = clean; non-zero = findings. Human-readable report in /tmp/mb.log.
```

Fix patterns: StrandHogg task-hijacking → add `launchMode="singleInstance"` + `taskAffinity=""`; TLS Certificate Transparency → raise `targetSdkVersion` to ≥29.

## Tool 2 — Narvy CLI (local SAST, pip-installed)

Install once into the venv: `~/sectools/mobsfscan-venv/bin/pip install narvy-cli`.

```bash
~/sectools/mobsfscan-venv/bin/narvy scan --output json app/src/main --file /tmp/nv.json
# NOTE: use `--output json ... --file <path>` — the `-o` short flag does NOT work here.
# Local scan needs no account. Read findings from /tmp/nv.json → summary.total_findings.
```

Fix pattern: AND-CONF-002 (app data backup) → set `android:allowBackup="false"` in AndroidManifest.xml when the app has no user data needing backup.

## Tool 3 — Semgrep (custom offline rules)

Rules live at `.github/semgrep/android-security.yml` and run fully offline (registry download is blocked). This build's rule schema has quirks:

- Use `patterns: [pattern: "..."]` form — NOT a bare `pattern-either:` at rule level (this build's validator rejects it).
- Java/Kotlin `pattern-either` strings are rejected by this build's schema; keep semgrep rules to XML-only patterns. (Hardcoded-secret detection in Java/Kotlin is covered by Narvy instead.)
- Semgrep inline XML comments (`<!-- semgrep: off -->`) are NOT honored by this build — do not rely on them.

```bash
~/sectools/mobsfscan-venv/bin/semgrep scan --config .github/semgrep/android-security.yml app/src/main --exclude-rules exported-activity > /tmp/sg.log 2>&1
```
`--exclude-rules exported-activity`: MainActivity MUST be `android:exported="true"` (required LAUNCHER component) — this is a false positive, excluded globally.

## Tool 4 — Detekt (Kotlin analysis + baseline)

CLI jar: download `detekt-cli-1.23.8-all.jar` (69MB) from GitHub releases to `/tmp/detekt-cli-1.23.8-all.jar`.

```bash
# Run + write a report (NO --output flag — use -r <id>:<path>):
java -jar /tmp/detekt-cli-1.23.8-all.jar --input app/src/main/java -r txt:/tmp/detekt.txt
# Generate/refresh a baseline of accepted findings:
java -jar /tmp/detekt-cli-1.23.8-all.jar --input app/src/main/java -cb -b .detekt-baseline.xml
# Verify clean (reports only issues NOT in baseline):
java -jar /tmp/detekt-cli-1.23.8-all.jar --input app/src/main/java -b .detekt-baseline.xml
```
Fix genuinely bad issues literally (unused params → remove param + update call sites; empty `else {}` blocks → convert to a statement block). Compose-convention findings are ACCEPTED via baseline — do NOT rename them:
- `FunctionNaming` on `@Composable` functions (AppNavHost/HomeScreen/LessonScreen) — PascalCase is correct Kotlin/Compose convention; detekt's default wants lowercase. Baseline them.
- `MatchingDeclarationName` (file AppNavHost.kt vs NavRoute class) — multiple top-level decls; baseline it.

## Tool 5 — Android Lint (platform checks)

```bash
cd <repo> && export JAVA_HOME=/opt/homebrew/Cellar/openjdk@17/17.0.18/libexec/openjdk.jdk/Contents/Home
gradle :app:lintDebug --console=plain > /tmp/lint.log 2>&1
```
Parse `app/build/reports/lint-results-debug.xml`. **0 Error-severity issues = clean.** Warnings are cosmetic (MissingApplicationIcon, GradleDependency "update available", OldTargetApi) and tolerated — do not chase them.

## Tool 7 — Konsist (architecture / dependency rules) ✅ WORKING

Real static-analysis architecture checks wired into the Gradle build. Coordinates: **`com.lemonappdev:konsist`, version `0.17.3`** — declared in `gradle/libs.versions.toml` and added to tests via `testImplementation(libs.konsist)` in `core/testing/build.gradle.kts`.

**Gotchas (each breaks the build if wrong):**
- WRONG coordinates 404: `consista/*` or `tschuchortdev/konsist`. The correct Maven group is **`com.lemonappdev`** (GitHub LemonAppDev/konsist, docs `docs.konsist.lemonappdev.com`).
- **Match the library's Kotlin ABI to your project, not its latest version.** `com.lemonappdev:konsist` **0.18.0 targets Kotlin 2.4.x** (stdlib-embeddable `2.4.21`); a newer stdlib breaks an older compiler with "expected version is X" (metadata mismatch). This project's Kotlin 2.1.0 needs **0.17.3** (built against Kotlin 2.0.x). When a new release breaks the build, check `pom.xml` for its kotlin-stdlib version and pick the newest release built against a Kotlin ≤ your compiler — don't chase `latest`.
- `Konsist.scopeFromProject()` still scans generated files under `build/` (Room/Hilt/KSP codegen) — the test slices those paths out to avoid false positives.

Run (JDK 17 required, same as other Gradle tasks):
```bash
cd <repo> && export JAVA_HOME=/opt/homebrew/Cellar/openjdk@17/17.0.18/libexec/openjdk.jdk/Contents/Home
gradle :core:testing:testDebugUnitTest --console=plain > /tmp/konsist.log 2>&1
# BUILD SUCCESSFUL + exit 0 = all architecture rules pass. Confirm it ran (not skipped):
grep -oE 'tests="[0-9]+" skipped="[0-9]" failures="[0-9]?" errors="[^"]*"' core/testing/build/test-results/testDebugUnitTest/TEST-com.example.core.testing.KonsistArchitectureTest.xml
```

Real test: `core/testing/src/test/kotlin/com/example/core/testing/KonsistArchitectureTest.kt` — mirrors the offline `DependencyRuleTest.kt` but drives the actual library. API shape (0.17.x): `Konsist.scopeFromProject()` → `.slice { it.hasPackage("com.example.app") || it.hasPackage("com.example.feature") }` → `.imports.filter { .name ... }`. `hasPackage(name)` is a **prefix match** (path containment); files expose `.moduleName` and `hasPackage(name)` via providers.

Architecture rules enforced (all currently pass): app+feature never touch Room/Keystore/network; features don't cross-depend (vacuous until feature sources exist); `:core:domain` has no android imports. If a rule fails, the assertion message names the offending import — fix by moving that dependency into `:core:*` or removing it.

NOTE: this is an *architecture* analyzer (package/dependency rules), not a security scanner — pair it with the tools above for full coverage.

## Tool 6 — Krit (SKIP)

Krit is not locatable in this sandbox: `google/krit` returns 404, and no GitHub search matches a Go-based Android/Kotlin scanner by that name (only unrelated KDE "Krita" and Kubernetes "kritis"). The filtered network also blocks release downloads. Skip Krit; note it as unlocatable.

## Fix Patterns Summary (fixable vs false-positive)

**Fix these:** hardcoded secrets; `allowBackup="true"`; weak crypto; unused params/imports; empty code blocks; real lint Errors.

**Do NOT touch (false positives / accepted):** MainActivity/launcher `exported="true"` (required); Compose PascalCase composables; baseline-accepted findings; vendored/generated code.

## Commit & Push

```bash
cd <repo> && git add -A && git commit -m "feat(security): fix SAST findings (mobsfscan/narvy/semgrep/detekt)" && git push origin feat/security-linters
```
Surgical fixes only — never refactor unrelated code. Never commit secrets/tokens/credentials (`[REDACTED]` if any appear).

## Output

- Fixed source committed/pushed to `feat/security-linters`.
- Summary of fixed vs false-positive findings per tool.

## Constraints

- Surgical fixes only; no unrelated refactors.
- Never auto-fix false positives. If unsure whether a finding is fixable, treat it as a false positive and note it.
- Krit excluded (not locatable in this environment).

## Reference Files

- `.github/semgrep/android-security.yml` — semgrep custom rules (offline).
- `.detekt-baseline.xml` — accepted detekt findings.
- `~/sectools/mobsfscan-venv/` — dedicated venv with mobsfscan + narvy-cli (not committed).
- `core/testing/src/test/kotlin/com/example/core/testing/KonsistArchitectureTest.kt` — real Konsist architecture tests (0.17.3).
- `gradle/libs.versions.toml` — konsist 0.17.3 coordinate + version entry.
