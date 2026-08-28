#!/usr/bin/env python3
"""Generate a synthesized Kannada research report from research_data.json using agy."""
import json, subprocess, os, sys
from datetime import datetime

# Read research data
with open('skills/deep-research/research_data.json') as f:
    data = json.load(f)

# Filter to news articles only (skip academic/reddit/social)
news_items = []
for item in data['all_items']:
    url = item.get('url', '')
    if any(skip in url for skip in ['ncbi.nlm', 'scholar.google', 'reddit.com', 'instagram.com', 'facebook.com']):
        continue
    news_items.append({
        'title': item.get('title', 'Untitled'),
        'content': (item.get('content', '') or '')[:2000],
        'url': url
    })

# Build the prompt
prompt = f"""You are a senior research analyst. Produce a concise Kannada research report about "Bengaluru 15-hour water supply disruption July 31".

The report should be ~600 words suitable for a Kannada news-style video script.

Synthesize from the following news sources. Focus on:
1. What happened: BWSSB announced 15-hour water cut on July 31 for emergency repairs
2. Why: Scour valve leak on 3000mm pipeline of Cauvery Stage 5
3. Affected areas: 100+ localities (list the key ones)
4. Timing: 6 AM to 9 PM
5. What residents should do: store water, use sparingly
6. Broader context: BWSSB warning about water crisis

Write in conversational Kannada news anchor style (podcast news anchor tone).
Start with a hook, deliver the news with detail, end with a sign-off.
Use spoken-word Kannada that flows naturally. Target ~600 words total.

IMPORTANT: Output ONLY the Kannada script text. No meta-commentary. No English unless it's a proper noun.

Here are the news sources:
"""

for i, item in enumerate(news_items[:10], 1):
    prompt += f"\n\nSOURCE {i}: {item['title']}\nURL: {item['url']}\n{item['content'][:2000]}"

prompt += "\n\nNow produce the Kannada news script."

# Save prompt to temp file
prompt_file = '/tmp/synthesis_prompt.txt'
with open(prompt_file, 'w') as f:
    f.write(prompt)

# Run agy
result = subprocess.run(
    ['agy', '--model', 'gemini-3.1-pro-high', '--effort', 'high', '--prompt', prompt],
    capture_output=True, text=True, timeout=180
)

output = result.stdout.strip()
if not output:
    output = result.stderr.strip()

print("=== KANNADA REPORT ===")
print(output)
print("=== END ===")

# Save the report
slug = "bengaluru-15-hour-water-supply-disruption-july-31"
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
report_dir = f'skills/deep-research/reports/{slug}-{timestamp}'
os.makedirs(report_dir, exist_ok=True)

with open(f'{report_dir}/report.md', 'w') as f:
    f.write(output)

print(f"\nReport saved to: {report_dir}/report.md")
