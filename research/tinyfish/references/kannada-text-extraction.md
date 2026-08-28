# Kannada Text Extraction via Tiny Fish

## Problem

When fetching Kannada poetry pages, the Tiny Fish fetch endpoint may return:
- Page metadata but no actual lyrics (e.g., YouTube pages with no transcript)
- Mix of English and Kannada text
- HTML tables that need parsing

## Solution: Kannada Character Detection

Extract Kannada text by checking Unicode range:
```python
for line in text.split('\n'):
    kannada_chars = sum(1 for c in line if 0x0C80 <= ord(c) <= 0x0CFF)
    if kannada_chars > 5:  # Significant Kannada content
        kannada_lines.append(line)
```

The range `0x0C80–0x0CFF` covers Kannada, Malayalam, and other South Indian scripts.

## Reliable Sources

For Kannada lyrics/poetry, prioritize:
1. **abhijnaa.wordpress.com** — Poetry with lyrics
2. **sallaap.blogspot.com** — Poetry collection
3. **lyricsinkannada.blogspot.com** — Song lyrics
4. **scholar articles** — For academic analysis

Avoid:
- YouTube pages (metadata only, no lyrics)
- Smule (captcha/bot blocked)
- Musixmatch (bot blocked)

## Search Query Patterns

Try multiple variants:
- `{poem} lyrics poems poetry kannada`
- `{poem} poet padagalu kavita`
- `{poem} full text meaning`

Fetch top 3 results. If lyrics extraction fails, use search snippets as fallback.

## Related Skills

- `kannada-poet` — Full Kannada poetry analysis pipeline
- `secrets-and-credentials` — Tiny Fish key handling
