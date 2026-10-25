---
name: webgl-scene-verification
description: Use when verifying a WebGL scene in a headless browser.
---

# WebGL Scene Verification (headless)

Verify and debug a browser-rendered 3D scene (Three.js or similar) when the image cannot be seen (vision analysis unavailable or untrustworthy).

## When to use

Use when a Three.js/WebGL scene (3D map, UI mockup, visualization) must be visually verified in a headless browser — especially when vision analysis is unavailable and a programmatic pass/fail signal is needed.

## Standing rules

- **Batch the whole verification into ONE `browser_exec` call** (load → wait ~2s → probe → capture): the tab can reset between calls (daemon restarts), and a probe in a later call may hit a blank tab and mislead. Re-apply `Emulation.setDeviceMetricsOverride` after `new_tab` — the viewport is lost.
- **Screenshot = ground truth.** `readPixels` on a buffer without `preserveDrawingBuffer` returns stale/unreliable pixels in this WebKit — never conclude a visual bug from readback alone; confirm against the composited PNG.
- **The GL buffer is DPR-scaled**: `setPixelRatio(2)` makes a 390×844 canvas a 780×1688 buffer — multiply projected screen coordinates by the pixel ratio before any `readPixels`.
- **CDP screenshots require `clip: {x, y, width, height, scale}`** — this Chrome build demands `scale` inside `clip`; a top-level `scale` is rejected.

## Procedure

1. Lock the viewport, load the scene (add a cache-buster `?cb=N` to defeat `file://` caching), wait ~2s. In the same call: ready-state check, JS probes, `Page.captureScreenshot` with a clip over the element rect.
2. **Color census (PIL)**: classify every pixel into palette families (thresholds tuned to the design's palette) plus explicit `WHITE` (R,G,B>250) and shifted-channel buckets; census the whole image plus per-expected-object windows. This is the pass/fail signal when vision is down.
3. Project scene anchors to screen: `v.project(camera)` → `sx=(v.x+1)/2*w, sy=(1-v.y)/2*h` (w,h = logical canvas size) to place the windows.

## Diagnostics (pixels disagree with the scene graph)

- **Color clamping = light overexposure.** If a color family renders pure white (255,255,255) or channel-shifted (e.g. green→cyan) while the scene graph holds the correct material colors, the summed lights (hemi+key+fill) × color are clamping at 255. Fix by scaling light intensities (per scene or per material), NOT by darkening materials. Re-verify with the same census.
- **Raycast cross-check**: `Raycaster.setFromCamera(pixelNdc, camera)` — if the hit object's material color ≠ the pixel color, the render state diverged from the scene graph (stale buffer/shader); trust the screenshot.
- **A/B via debug flags**: expose URL-hash flags in the load handler (`noIcon`, `noFace`, `mat1`…); load variants in one call and census each; the suspect component is the variant whose removal kills the anomaly.
