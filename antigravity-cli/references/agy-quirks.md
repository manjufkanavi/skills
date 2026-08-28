# agy CLI Quirks — Reference Notes

## Key Discoveries

### 1. Output Wrapping
agy wraps ALL output in single quotes with escaped characters:
```
'{"description": "\\\"text\\\"", "items": [1,2,3]}\\n'
```
Must strip outer `'...'` and unescape `\\n`→`\n`, `\\"`→`"`.

### 2. Shell Quoting Failure
```bash
agy -p 'The shell eats everything between quotes'  # BROKEN — empty prompt
```
This is the #1 cause of agy failures. **ALWAYS use stdin piping.**

### 3. Prefix Text
agy agent sometimes adds prose before JSON:
```
ಪ್ರಣಾಮಗಳು. As a seeker of truth...{"key": "value"}
```
Solution: find first `{` to last `}`+1, not start of output.

### 4. Prompt Length vs Quality
- Short prompts → minimal JSON (only 1 field)
- Long, descriptive prompts → complete JSON with all fields
- Provide role, context, and explicit output schema

### 5. File References
`@/tmp/lyrics_kannada_poet.md` works for reading file content into prompts.
Use consistent temp file naming: `/tmp/lyrics_kannada_poet.md`.

### 6. Model Choice
- `gemini-3.5-flash-medium` — best balance
- `gemini-2.0-flash` — too terse, misses fields
- `gemini-3.1-pro` — not available, use medium

### 7. Timeout
agy takes 15-120 seconds. Set timeout ≥ 180s in subprocess.run().

## Comparison: Gemini CLI vs agy

| Feature | Gemini CLI | Antigravity CLI (agy) |
|---------|-----------|----------------------|
| Command | `gemini -p "prompt"` | `agy -p "prompt"` via helper |
| Auth | API key | Google Sign-In |
| Output format | Direct JSON | Quoted JSON |
| Shell quoting | Works inline | FAILS — use stdin |
| @file refs | Yes | Yes |
| Rate limits | 429 on free tier | N/A (uses agy infra) |
| Status | Deprecated | Active |
| Model | gemini-2.0-flash | gemini-3.5-flash-medium |