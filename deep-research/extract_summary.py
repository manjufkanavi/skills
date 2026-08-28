#!/usr/bin/env python3
"""Extract summary of research_data.json for synthesis."""
import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)

print(f"TOPIC: {data['topic']}")
print(f"QUERIES: {data['total_queries']}")
print(f"ROUNDS: {data['rounds']}")
print(f"WEB: {data['web_count']}")
print(f"PDF: {data['pdf_count']}")
print(f"RESEARCH: {data['research_count']}")
print(f"ALL_ITEMS: {len(data['all_items'])}")

for theme_key in ['definition', 'evolution', 'mechanics', 'challenges', 'applications', 'future']:
    items = data['themes'].get(theme_key, [])
    print(f"\n=== THEME: {theme_key} ({len(items)} items) ===")
    for i, item in enumerate(items[:5]):
        title = item['title'][:200]
        content = item['content'][:2000]
        url = item['url'][:200]
        print(f"\n--- Source {i+1}: {title} ---")
        print(f"URL: {url}")
        print(f"CONTENT:\n{content}")
