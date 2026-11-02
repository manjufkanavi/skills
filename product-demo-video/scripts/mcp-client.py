#!/usr/bin/env python3
"""Drive a locally-launched Playwright MCP HTTP server (fallback driver).

Use this when the current Hermes session does NOT have native
mcp_playwright_browser_* tools (Playwright MCP not registered in config.yaml).
Pair with scripts/launch-mcp.sh, which prints the URL.

IMPORTANT — session lifetime:
  Every client that connects gets a browser; when the LAST client disconnects
  the server closes the browser. So multi-step flows MUST run in --script mode
  (one persistent session executing many calls). One-shot calls get a fresh
  browser and any earlier state is gone.

Usage:
  # one-shot (single call; fresh browser, closed on exit)
  mcp-client.py <url> <tool> [json-args] [--timeout S] [--save-images DIR]

  # script mode (persistent session; recommended for any multi-step flow)
  mcp-client.py <url> --script calls.jsonl [--timeout S] [--save-images DIR]

calls.jsonl — one JSON object per line, in order:
  {"tool": "browser_navigate", "args": {"url": "https://example.com"}}
  {"tool": "browser_start_video", "args": {"filename": "scene_01.webm",
    "size": {"width": 1280, "height": 720}}}
  "browser_stop_video"            (bare tool name = no args)

Output: "### <index> <tool>" then the result text per call. Image content is
summarized, or saved to --save-images DIR (PNG) for vision_analyze.
A tool-level isError is printed and does NOT abort the script; a dropped
connection exits 3. Exit 0 = all calls ok, 2 = at least one tool error.
"""
import asyncio
import base64
import json
import os
import sys
from datetime import timedelta


def print_result(idx, tool, res, save_images):
    print(f"### {idx} {tool}")
    n_img = 0
    for c in res.content:
        ctype = getattr(c, "type", None)
        if ctype == "text":
            print(c.text)
        elif ctype == "image":
            n_img += 1
            if save_images:
                os.makedirs(save_images, exist_ok=True)
                mime = getattr(c, "mimeType", "") or ""
                ext = "png" if "png" in mime else ("jpeg" if "jpeg" in mime else "bin")
                p = os.path.join(save_images, f"{tool}_{n_img}.{ext}")
                with open(p, "wb") as f:
                    f.write(base64.b64decode(c.data))
                print(f"[image saved: {p}]", file=sys.stderr)
            else:
                print(f"[image: {mime}, {len(c.data)} b64 chars]", file=sys.stderr)
    sc = getattr(res, "structuredContent", None)
    if sc:
        print(f"[structured: {json.dumps(sc)[:400]}]")
    if res.isError:
        print("[TOOL ERROR — see text above]", file=sys.stderr)


async def session(url, timeout_s, calls, save_images):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    errors = 0
    async with streamablehttp_client(url, timeout=timedelta(seconds=max(timeout_s, 20))) as (r, w, _):
        async with ClientSession(r, w) as session_obj:
            await session_obj.initialize()
            for idx, call in enumerate(calls, 1):
                if isinstance(call, str):
                    tool, args = call, {}
                else:
                    tool = call.get("tool", "?")
                    args = call.get("args") or {}
                try:
                    res = await asyncio.wait_for(session_obj.call_tool(tool, args), timeout=timeout_s + 30)
                    print_result(idx, tool, res, save_images)
                    if res.isError:
                        errors += 1
                except asyncio.TimeoutError:
                    print(f"### {idx} {tool}\n[TIMEOUT after {timeout_s + 30}s]", file=sys.stderr)
                    errors += 1
                except Exception as e:
                    print(f"### {idx} {tool}\n[CALL ERROR: {e}]", file=sys.stderr)
                    errors += 1
    return errors


def parse_args(argv):
    timeout = 60.0
    save_images = None
    script = None
    pos = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--timeout" and i + 1 < len(argv):
            timeout = float(argv[i + 1]); i += 2; continue
        if a == "--save-images" and i + 1 < len(argv):
            save_images = argv[i + 1]; i += 2; continue
        if a == "--script" and i + 1 < len(argv):
            script = argv[i + 1]; i += 2; continue
        pos.append(a); i += 1
    return timeout, save_images, script, pos


def load_calls(path):
    calls = []
    with open(path) as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                calls.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.exit(f"bad calls.jsonl line {ln}: {e}")
    if not calls:
        sys.exit(f"empty script: {path}")
    return calls


def main():
    timeout, save_images, script, pos = parse_args(sys.argv[1:])
    if not pos:
        print(__doc__)
        sys.exit(64)
    url = pos[0]
    try:
        if script:
            calls = load_calls(script)
            errors = asyncio.run(session(url, timeout, calls, save_images))
            print(f"[summary] {len(calls) - errors}/{len(calls)} calls ok", file=sys.stderr)
            sys.exit(2 if errors else 0)
        tool = pos[1] if len(pos) > 1 else None
        if not tool:
            print(__doc__)
            sys.exit(64)
        args = json.loads(pos[2]) if len(pos) > 2 and pos[2].strip() else {}
        errors = asyncio.run(session(url, timeout, [ {"tool": tool, "args": args} ], save_images))
        sys.exit(2 if errors else 0)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[connection error: {e}]", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
