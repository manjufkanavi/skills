# Compose Debugging for Screenshot Capture

Crashes and navigation gaps that surface while driving a running Android app. Fix these before the target screen can be captured.

## RoundedCornerShape with a bare integer crashes
`RoundedCornerShape(999)` (no `.dp`) resolves to the **percent** overload, so `999` is read as a percentage and throws:
```
ja.lang.IllegalArgumentException: The percent should be in the range of [0, 100]
```
The crash happens at composition time (e.g. inside a `Card`/`Button` shape), not later, so it kills the whole screen. Fix: pass a dp value — `RoundedCornerShape(999.dp)`. This recurs wherever a shape is built from a bare number; grep the source for `RoundedCornerShape(<number>)` and add `.dp` to each.

## Bottom navigation that never navigates
A bottom nav with `onClick = { selected = index }` sets a variable that nothing reads, so tapping nav items does no navigation — the app stays put. Add a `LaunchedEffect(selected)` that calls `navController.navigate(concreteRoute)`. Until then the tab is dead code and its screen cannot be reached by tapping.

## Navigating a route template passes literal arguments
A constant like `Route.QUIZ = "quiz/{topicId}"` is a **template**. Navigating with `navController.navigate(Route.QUIZ)` sends the literal string `{topicId}`, so lookups keyed on that value return null (e.g. `topicById("{topicId}")` → "Topic not found\`). Navigate to a **concrete** route with the real argument: `navController.navigate("quiz/ec2")`.

## Toggling app state when /data is read-only
Some apps gate screens on persisted flags (e.g. "certificate unlocked only after passing an exam") stored in `shared_prefs`. On a locked-down emulator the app data dir is **read-only**: writing via `run-as ... cat > shared_prefs/<file>.xml` fails with "Read-only file system", and `adb root`/remount is unavailable. You cannot change the persisted value.

Work around it by updating the flag's **in-memory** state instead of disk. The app exposes flags as a `MutableStateFlow` observed through Compose (`observe()`); writing that flow updates memory first, so the UI reflects it even when the disk write fails. Call a method that sets the flow in-memory (e.g. `markExamPassed()` / a reset) — no persistence required.

Practical effect: one build with temporary debug buttons (or a single method call) lets you flip between states and capture each, without root or writable storage. Remove the temporary controls before shipping — they are dev-only.

