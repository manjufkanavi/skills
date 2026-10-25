# Compose State Handling (Compile & Correctness)

Recurring traps when writing/fixing Jetpack Compose state code. Traps 1–2 cause compile errors; trap 3 is a runtime perf trap.

## Trap 1: `rememberSaveable` map — delegate vs `.value`
Passing a delegated-map property where a concrete `Map<K, V>` is expected fails type-checking, and keyed reads misbehave.

WRONG — the `by rememberSaveable { mutableStateMapOf(...) }` delegate exposes a proxy whose static type is not exactly `Map<K, V>`: it fails a concrete-`Map` parameter and keyed reads return the wrong element type:
```kotlin
var selected by rememberSaveable { mutableStateMapOf<String, String>() }
ResultsView(questions, selected)          // actual type is String but Map expected
val v = selected[q.id]                     // returns the wrong element type instead of String?
```

RIGHT — hold an explicit `MutableState<Map>` and access it via `.value`:
```kotlin
val selected = rememberSaveable { mutableStateOf(emptyMap<String, String>()) }

// read entries / size:
val v = selected.value[q.id]              // String?
QuizProgressHeader(..., answered = selected.value.size)

// write — assign the WHOLE map so Compose recomposition fires (mutating an entry in
// place is not observed by the composition):
selected.value = selected.value + (q.id to chosen)   // immutable add -> new map value
```
Why: an explicit `mutableStateOf(emptyMap())` is a real `MutableState<Map<K, V>>`; `.value` gives the map. Assigning the whole map (not mutating one entry) changes the state value, which is what recomposition observes.

## Trap 2: parameter shadowing a captured state var
A function parameter sharing a name with an outer `var` makes assignments inside the body target the **parameter** (a val), producing "val cannot be reassigned".
```kotlin
fun QuizScreen() { ... var currentQ by rememberSaveable { mutableStateOf(0) } ...
    QuizProgressHeader(currentQ = currentQ, ...)      // call site passes the state value
}

private fun QuizProgressHeader(currentQ: Int) {       // PARAMETER shadows the outer var
    ... .clickable { currentQ = i }                   // reassigns the val PARAMETER -> error
}
```
Fix: rename the parameter (e.g. `index`) and thread state with an explicit callback, e.g. add `onSelectQuestion: (Int) -> Unit` and call it from the click; at the call site pass `{ currentQ = it }`. Reassign inside the scope that owns the state var.
Why: a parameter shadows any outer variable of the same name, so `x = ...` reassigns the local parameter (a val), not the captured state. Assign inside the owning scope or via a callback that does it there.

## Trap 3: continuous controls — commit on release, never per frame
`Slider`/drag/scrub controls fire `onValueChange` **every frame of the drag**. Writing that value straight into a persisted source (a SharedPreferences-backed property, a DB row) does disk I/O on the main thread per frame and storms recomposition. Hold a local drag value; commit once per gesture:

```kotlin
WRONG — persisted write per frame:
Slider(value = AppState.ttsSpeed, onValueChange = { AppState.ttsSpeed = it }, valueRange = 0.5f..3f)

RIGHT — local state while dragging, one commit on release:
var speed by remember { mutableStateOf(AppState.ttsSpeed) }
Slider(
    value = speed,
    onValueChange = { speed = it },                    // local: cheap, per frame
    onValueChangeFinished = { AppState.ttsSpeed = speed },  // one write per gesture
    valueRange = 0.5f..3f,
)
```
Why: local `remember` state is exactly what per-frame updates are for; the persisted source mutates once per completed gesture. (For a glider with a display label, format the *local* value so the label tracks the drag, and round/clamp only at commit time.)
