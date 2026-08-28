#!/usr/bin/env python3
"""Extract evolution, mechanics, challenges, applications, future themes."""
import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)

for theme_key in ['evolution', 'mechanics', 'challenges', 'applications', 'future']:
    items = data['themes'].get(theme_key, [])
    print(f"\n=== THEME: {theme_key} ({len(items)} items) ===")
    for i, item in enumerate(items[:10]):
        title = item['title'][:200]
        content = item['content'][:1500]
        url = item['url'][:200]
        print(f"\n--- Source {i+1}: {title} ---")
        print(f"URL: {url}")
        print(f"CONTENT:\n{content}")
