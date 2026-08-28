import os, sys, re, json, time, urllib.parse, concurrent.futures, urllib.request
from pathlib import Path

TINYFISH_API_KEY = os.environ.get('TINYFISH_API_KEY', 'sk-tinyfish-vHbgNi2R-tVLAXFixslJ3lk5iz71dIsE')
TINYFISH_SEARCH_URL = 'https://api.search.tinyfish.ai'
TINYFISH_FETCH_URL = 'https://api.fetch.tinyfish.ai'

def search(query, max_results=10):
    try:
        url = f'{TINYFISH_SEARCH_URL}?query={urllib.parse.quote(query)}'
        req = urllib.request.Request(url, headers={'X-API-Key': TINYFISH_API_KEY})
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result.get('results', [])
    except Exception as e:
        print(f'  Search failed: {e}')
        return []

def fetch(url):
    try:
        import urllib.request
        data = json.dumps({'urls': [url], 'format': 'markdown'}).encode()
        req = urllib.request.Request(TINYFISH_FETCH_URL, data=data, headers={
            'X-API-Key': TINYFISH_API_KEY, 'Content-Type': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            pages = result.get('results', [])
            if pages:
                content = pages[0].get('text', '') or pages[0].get('content', '')
                title = pages[0].get('title', '')
                return content, title
            return '', ''
    except Exception as e:
        print(f'  Fetch failed: {e}')
        return None, ''

queries = [
    'loop engineering AI coding agents',
    'loop engineering vs prompt engineering Claude Code',
    'loop engineering Boris Cherny Karpathy',
    'loop engineering CI/CD pipeline adaptation',
    'loop engineering common problems failures',
    'loop engineering fixes solutions',
    'loop engineering feedback loop architecture',
    'loop engineering context engineering harness engineering',
    'loop engineering production deployment issues',
    'loop engineering testing validation debugging',
    'loop engineering token cost overhead',
    'loop engineering multi-agent coordination',
    'loop engineering error handling retry',
    'loop engineering observability monitoring',
    'loop engineering human in the loop HITL',
    'loop engineering best practices guidelines',
    'loop engineering enterprise adoption challenges',
    'loop engineering security compliance risks',
    'loop engineering scalability limitations',
    'loop engineering tooling ecosystem',
    'loop engineering AWS Azure GCP',
    'loop engineering open source tools',
    'loop engineering research paper',
    'loop engineering survey 2026',
    'loop engineering future trends',
    'loop engineering comparison traditional CI/CD',
]

print('Searching with targeted queries...')
all_results = []
BATCH_SIZE = 5
for batch_start in range(0, len(queries), BATCH_SIZE):
    batch = queries[batch_start:batch_start + BATCH_SIZE]
    with concurrent.futures.ThreadPoolExecutor(max_workers=BATCH_SIZE) as pool:
        futures = {pool.submit(search, q): idx for idx, q in enumerate(batch)}
        batch_results = [None] * len(batch)
        for fut in concurrent.futures.as_completed(futures):
            idx = futures[fut]
            try:
                res = fut.result()
                batch_results[idx] = res
            except:
                batch_results[idx] = []
        for res in batch_results:
            if res:
                all_results.extend(res)
    if batch_start + BATCH_SIZE < len(queries):
        time.sleep(0.3)

print(f'Got {len(all_results)} search results')

seen = set()
unique_urls = []
for r in all_results:
    url = r.get('url', '')
    if url and url not in seen:
        seen.add(url)
        unique_urls.append(url)
    if len(unique_urls) >= 50:
        break

print(f'Unique URLs: {len(unique_urls)}')

print('Fetching pages...')
all_content = []
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(fetch, u): u for u in unique_urls}
    for fut in concurrent.futures.as_completed(futures):
        url = futures[fut]
        try:
            content, title = fut.result()
            if content and len(content) > 100:
                all_content.append({'title': title or url.split('/')[-1], 'content': content, 'url': url})
        except:
            pass
        time.sleep(0.1)

print(f'Fetched {len(all_content)} pages')

# Write to workspace
report_dir = Path('/Users/manjunathkanavi/.nanobot/workspace/personal_bot/deep-research/reports')
report_dir.mkdir(parents=True, exist_ok=True)

with open(report_dir / 'loop_engineering_raw.json', 'w') as f:
    json.dump(all_content, f, ensure_ascii=False)

print(f'Saved {len(all_content)} items to workspace')
print('Data collection complete.')
