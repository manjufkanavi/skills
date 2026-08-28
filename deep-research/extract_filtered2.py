#!/usr/bin/env python3
"""Extract key content from research_data.json for synthesis."""
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
    for i, item in enumerate(items):
        title = item['title'][:200]
        content = item['content'][:1500]
        url = item['url'][:200]
        # Skip job postings and irrelevant
        if any(kw in content.lower() for kw in ['job summary', 'job description', 'required qualifications', 'birmingham', 'dallas', 'texas', 'alabama', 'contract to hire', 'direct hire', 'position summary', 'key responsibilities', 'job duties', 'what you will do', 'qualifications:', 'bachelor', 'degree in']):
            continue
        print(f"\n--- Source {i+1}: {title} ---")
        print(f"URL: {url}")
        print(f"CONTENT:\n{content}")
