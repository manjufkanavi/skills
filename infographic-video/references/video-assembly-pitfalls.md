# Video Assembly Pitfalls (macOS + ffmpeg 8.x)

Durable, class-level lessons for assembling narration+image videos into MP4
(used by `infographic-video`, `tech_teacher`). These are NOT one-off tool
breakages — they recur whenever you build a video with ffmpeg on this machine.

## 1. `drawtext` is not compiled into the system ffmpeg

On this host's macOS ffmpeg build, the `drawtext` filter is **absent**.
Attempting `[v]drawtext=text='hi'` fails with:

```
[AVFilterGraph @ ...] No such filter: 'drawtext'
```

**Workaround:** render any title/overlay text as a PNG with `cairosvg`
(crisp, anti-aliased), then composite it over the video with ffmpeg's
`overlay` filter:

```bash
# render title bar PNG (cairosvg) then overlay at top-left
ffmpeg -i scene.png -i titlebar.png -filter_complex \
  "[0][1]overlay=0:0" out.mp4
```

Do NOT try to fix this by reinstalling ffmpeg — the filter simply isn't in the
build. Use cairosvg for all text-as-image needs (titles, captions, lower thirds).

## 2. cairosvg on macOS needs DYLD_LIBRARY_PATH set before import

`import cairosvg; cairosvg.svg2png(...)` silently fails with:

```
OSError: no library called "cairo-2" was found
```

Set the dylib search path in your environment **before** importing cairosvg:

```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib   # Homebrew libs (libcairo, etc.)
```

This is an environment-setup step the user can fix; it is not a cairo bug.
When calling from Python, either export before launching the interpreter or set
`os.environ["DYLD_LIBRARY_PATH"]` at the very top of your script before any
cairosvg import.

## 3. ffmpeg `-map` must reference the FINAL output label, not an intermediate one

If your filter graph consumes a labeled pad (`[scaled]`) and then produces
`[outimg]`, you cannot `-map "[outimg]"` after also using it downstream. Map the
**terminal** label only:

```bash
# WRONG  -> "Output with label 'outimg' does not exist / already used"
-filter_complex "[i]scale=...,pad=[scaled];[scaled][bar]overlay[outimg]" \
-map "[outimg]"

# RIGHT  -> map the final [out] label produced by the last filter
-filter_complex "[i]scale=...,pad=[scaled];[scaled][bar]overlay[outimg]" \
-map "[out]"    # where [out] is the terminal label of the graph
```

Rule: each filtergraph output label can be used by at most one `-map`. If you
still need the intermediate, split it with a second `split` filter.

## 4. Odd dimensions break libx264 (requires even width AND height)

`scale` + `pad` can yield an odd dimension (e.g. 1920×1081), which libx264
rejects:

```
[libx264] height not divisible by 2 (1920x1081)
```

Fix by forcing a yuv420p pixel format in the chain (this rounds dimensions to
even) and/or rounding pad output. A reliable pattern:

```bash
-filter_complex "[i]scale=-1:{H}:force_original_aspect_ratio=increase," \
  "format=yuv420p,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black[scaled]"
```

`format=yuv420p` guarantees even dimensions and the yuv420p layout libx264
needs. Always end with `-pix_fmt yuv420p` on the output too as a belt-and-braces.

## 5. concat demuxer needs an actual FILE path, not a directory

Passing a **directory** (e.g. `--outdir` pointing at the work folder) as the
output makes ffmpeg fail:

```
Unable to choose an output format for '<dir>'; use a standard extension ...
Error initializing the muxer for '<dir>': Invalid argument
```

The concat demuxer output must be a real `.mp4` **file** path. Keep `manifest.out`
as the absolute output file, and run:

```bash
python3 build_video.py manifest.json            # uses manifest.out (the .mp4)
# NOT: --outdir <dir>   which overrides out with a directory and breaks muxing
```

## 6. Per-scene A/V sync: loop the image and cap with `-t`

To lock each scene's still image to its own narration length, loop the image
and cap the clip with `-t` equal to the audio duration:

```bash
ffmpeg -y -loop 1 -t {dur}s -i image.png -i audio.mp3 \
  -filter_complex "[0][1]overlay=0:0[outv]" \
  -map "[outv]" -map "1:a" -t {dur}s \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -c:a aac -b:a 192k clip.mp4
```

`scene_duration()` should read duration via `ffprobe -show_entries format=duration`,
rounded up to whole seconds (min 1). The concat demuxer then stitches clips with
no visible seam because each clip is already exactly its audio length.

## 7. kokoro-tts-production depends on SSH to fetch the API key (diagnose, don't hard-fail)

`kokoro_tts.py` fetches its bearer key over SSH from the homeserver
(`mkanavi@192.168.0.116`, key `~/.ssh/home-server`) at call time — no local
secret is stored. If the homeserver is unreachable, every TTS request fails with:

```
[ERROR] Could not fetch API key from mkanavi@192.168.0.116 over SSH (returncode=255)
```

or a downstream `HTTP Error 502: Bad Gateway` when the key fetch returns empty.
This is **environment-dependent and transient** — retry after a short wait, or
verify connectivity first:

```bash
ssh -o ConnectTimeout=8 -i ~/.ssh/home-server mkanavi@192.168.0.116 "echo reachable"
```

Do NOT bake "TTS is broken / homeserver unreachable" into any skill as a hard
constraint; it resolves when the server is back. Only record that the key *must*
be fetched over SSH (see above) as a durable fact.

## 8. subprocess: match `text=` with string input, or pass bytes without it

When feeding text via stdin to a child process:
- `subprocess.run(cmd, input=bytes_data)` → do **not** pass `text=True` (it
  will try to `.encode()` bytes → AttributeError). Decode stderr with
  `proc.stderr.decode("utf-8", "replace")` when in bytes mode.
- Or use `text=True` and pass a **str** for both input and stderr.

Keep the two consistent to avoid confusing "bytes has no encode" errors.
