# python-pptx 1.0.2 quirks (and portable workarounds)

The `pptx-maker` engine was debugged against **python-pptx 1.0.2**, an old build that
lacks a high-level animation API and has several API-name differences. The workarounds
below are already encoded in `scripts/deck_builder.py`, but know them when extending or
debugging the engine — they are portable to any old python-pptx build.

## Enum name differences (this build)

| Use this | Not this |
|----------|----------|
| `XL_LEGEND_POSITION` | `XL_LEGACY_POSITION` |
| `XL_DATA_LABEL_POSITION` | `XL_LABEL_POSITION` |
| `XL_CHART_TYPE.BAR_CLUSTERED` | `CHART_TYPE_CLUSTERED_BAR` |
| `XL_CHART_TYPE.COLUMN_CLUSTERED` | `CHART_TYPE_CLUSTERED_COLUMN` |

## API gaps & workarounds

1. **No animation API.** `Shape` has no `enter_effect` / `timing`. The engine hand-crafts
   `<p:timing> / <p:seq>` XML via lxml (`_add_seq`). Time-action (`st`): after=196608,
   with=131073, click=-2147483647. `type` (ST_SeqType) selects the animation; the
   `<p:effectLst>` child disambiguates.
2. **`plot.has_data_labels = True`** must be set *before* accessing `plot.data_labels`,
   else `ValueError: plot has no data labels`.
3. **Font-size minimum is `Pt(1)`.** `int(h * factor)` truncates to 0 for small metric
   cards → clamp with `max(int(...), N)`.
4. **`Table` lacks `_element`.** Capture the `TableShape` (the object returned by
   `slide.shapes.add_table(...)` *before* `.table`) and animate that — it has `.slide`.
5. **`text_frame` has no `.slide`.** Resolve the owning slide by XML walk:
   `<a:txBody>` → `<p:sp>` → `<cSld>`.
6. **`Shape` has no `in_backdrop`.** The background shape is already the first shape
   (at back) — simply do not call it.
7. **`FillFormat.fore_color`** (not `forg_color`).
8. **text_frames have no `.set()`.** Never call `shape.set(...)` on a text_frame (the dead
   `data-speed` attribute was removed).
9. **grouped `series` entries** are `[name, v1, v2, ...]` (name + N values) — unpack
   `entry[0]` and `entry[1:]`, not a 2-tuple.
10. **`row_colors[r]` can index out of range** — clamp with `min(r, len(row_colors)-1)`.

## Animation effect tables

- **ENTER (entry):** appear=0, fly=1, push=2, split=3, wor=8, zoom=9, fall=10.
- **EMPH (emphasis):** compress=0, expand=1, glow=2, pulse=3, resize=4, skew=5.

## Debugging recipe when a build throws

1. Confirm the enum name exists: `python -c "from pptx.enum.chart import XL_CHART_TYPE; print([e for e in dir(XL_CHART_TYPE) if 'BAR' in e or 'COLUMN' in e])"`.
2. If `enter_effect` / `timing` are missing → hand-craft `<p:seq>` (see `_add_seq`).
3. If `data_labels` raises → set `plot.has_data_labels = True` first.
4. If a shape lacks an attribute → it is probably a `text_frame` or `Table`; resolve the
   owning slide via the XML walk above, or animate the wrapper `TableShape`.
