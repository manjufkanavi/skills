# Mockup render → capture → verify (browser tool)
The capture pipeline for audition screenshots of HTML mockups — plain 2D SVG/HTML pages AND full 3D/scene pages (three.js journey-map dioramas). The owner picks from the pixels, so every pixel sent must pass the verification gate at the bottom.

## Build
- No local HTTP server (the sandbox blocks persistent processes): `curl` the needed libs into the scratch dir beside the HTML (e.g. `three.min.js` r128 from cdnjs) and open via `file://` — the browser loads file:// URLs fine.
- One HTML file per audition; variant selected by URL hash (`#d=N`). `new_tab(file://…#d=N)` is a full reload, so hash-switching is the cheapest way to render many variants from one file.
- `file://` caching: after editing the HTML, a re-`new_tab` on the same URL can serve the cached document — append `?cb=<n>` before `#hash` and confirm the new code actually loaded (probe a marker global/flag in-page) before debugging anything else.
- The phone frame self-scales to the viewport (`transform: scale(min(vw/W, vh/H))`) so a viewport-sized capture always contains the whole frame.

## This browser is a WebKit build — CSS/canvas gotchas (each cost real debugging time)
- The `inset` shorthand is silently ignored: a `position:absolute; inset:0` canvas falls back to its width/height ATTRIBUTES (a 2× buffer) and the parent's `overflow:hidden` clips it to a quarter — the scene renders but content vanishes. Use explicit `top:0;left:0;right:0;bottom:0` on every absolutely-positioned layer.
- Even with explicit edges this WebKit sizes the `<canvas>` from its width/height attributes when the CSS box is ambiguous — pin `canvas.style.width/height` in the resize handler, then `renderer.setSize(w, h, false)`.
- `canvas.getContext('webgl')` returns null when three.js created a webgl2 context — that probe lies. Check `renderer.context` / `renderer.capabilities` instead.

## Before any capture
- Pin the viewport: `cdp("Emulation.setDeviceMetricsOverride", width=1280, height=633, deviceScaleFactor=1, mobile=False)` + `window.dispatchEvent(new Event('resize'))`, then re-verify the element rects. The harness window resizes mid-session (dpr/innerWidth drift) and desyncs rect ↔ buffer.
- Tabs reset between `browser_exec` calls (a call can land on `about:blank`). Guard the top of every call: read `location.href`; if not on the target URL, `new_tab(url)` first.

## Capture
- `capture_screenshot()` prints no usable file path in this setup — capture via CDP: `cdp("Page.captureScreenshot", format="png", clip={x,y,width,height,scale:2}, captureBeyondViewport=True)`, base64-decode, write the file. clip = the phone element's `getBoundingClientRect()` in CSS px; `scale:2` gives 2× output. This Chrome requires `scale` inside the clip object and `width`/`height` keys (`w`/`h` fail deserialization; a top-level `scale` is rejected).
- Long flat pages (terms/about): set the frame `height:auto` so the clip covers the whole content, and `captureBeyondViewport=true` still captures beyond the pinned viewport — no internal scroll, one tall PNG per page.

## JS interop (browser_exec `js()` / `cdp()`)
- Multi-line JS: use Python triple-quoted strings — a literal newline inside a single-quoted `js("…")` is a SyntaxError that kills the whole call.
- `cdp()` returns a dict: the base64 payload is `res["data"]`; base64-decode that, not the dict.
- Top-level `const`/`let` in a classic script are reachable as bare identifiers from eval but not on `window` — `js("typeof renderer")` is the right global probe, and it doubles as the tab-reset detector (a reset tab answers `undefined`).

## Render forensics (when pixels are the wrong colour)
- **Overexposed light is the classic "everything looks white/cyan" bug.** A material rendering as pure white or a channel-maxed colour (e.g. 156,255,255) while its base colour is mid-range means the light sum exceeds 1.0 and the output clamps: out = colour × (hemi + key·N·L + fill·N·L). Compute the top-face multiplier and scale ALL lights so it is ≈ 1.0 (0.95 hemi + 0.62 key + 0.28 fill → × 0.58 for stylised candy palettes). The brightest pieces and any far piece faded toward a light ground clamp first — check those, and read the true light level off the darkest piece.
- **`gl.readPixels` is not the verdict.** This WebKit build has been observed serving stale/garbage buffer contents even with `renderer.render` + `readPixels` in one task — buffer values contradicted the composited frame while raycasts confirmed the scene was correct. The DOM screenshot is ground truth; readPixels is a cross-check only.
- **`renderer.setPixelRatio(2)` ⇒ the drawing buffer is 2× the CSS size.** readPixels coordinates must be doubled (NDC → buffer: `(x+1)/2*bufW, (1−y)/2*bufH`). A 1× probe against a 2× buffer samples the wrong scene quadrant and masquerades as "objects missing".

## three.js scene fit (perspective camera)
- After every `camera.lookAt()`, before `Vector3.project()`: `camera.updateMatrixWorld(); camera.matrixWorldInverse.copy(camera.matrixWorld).invert()` — lookAt does NOT refresh matrixWorldInverse; a stale matrix silently corrupts every projection-based fit/solver.
- NDC y=+1 is the TOP of the screen; screen fraction from top = (1 − y)/2.
- Fit with two independent bisections (distance → projected span; aim height → vertical centre), a few outer rounds. Evaluate both bisection bounds first and confirm the monotonic direction before trusting the solver (one flipped direction runs the search to the boundary).
- For a multi-node meandering map the default is a near-top-down elevation (~70-75°, board-game look). Shallow elevations (~50-55°, chosen to show 3D side-walls) can also fit, but the fit converges to a much farther camera — pieces render small, and an absolute-distance depth fade tuned to a closer camera then washes every piece out. With a shallow camera, make the depth fade **relative** (normalize each piece's distance to the map's own min/max, smoothstep, cap ~50%) and exempt the active/hero piece from fading.

## Verify with pixels (vision provider down or unreliable)
Project every map object through the live camera (matrix updated as above) → expected screen fraction → PIL-classify a window centred on each. All three must pass before the image is sent to the owner:
1. every node fraction inside ~[0.06, 0.94] of the screen height
2. per-node window dominated by the expected state colour (e.g. jade `g>110 && g>r+50 && g>b+20`; gold `r>190 && 120<g<215 && b<115 && r>g+40`)
3. the N variant images are pairwise unique (md5) and each carries its signature accent colour

### Flat UI pages (settings/screens mockups, no 3D)
Same dual gate, census tuned for text rather than map objects: (1) **DOM** — `document.body.innerText` must contain every key string of the view, and zero text-bearing elements may have a <1px box (a 0-width column leaves no trace in a screenshot). (2) **Pixels at FULL resolution** — never run the census on a downsampled image with a tight tolerance around a reference colour: a ≤¼ downscale averages 1–3px text strokes into the background, so an exact-match count of the ink/primary colour returns 0.000 on a fully rendered page (a false "content missing" assert). Classify full-res pixels with windows, not exact matches: dark text (r<130 & g<130 & b<125), accent (r>180 & 40<g<130 & b<90), background (±10 of the theme bg). Pass = all key strings present, zero zero-size text nodes, dark-px fraction > ~0.2% with row-span covering the expected content range, correct background fraction, per-image md5 pairwise unique.
