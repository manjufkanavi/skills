# Security / "weapon-landscape" Research

Domain note for queries that resolve to a **catalogue of tools** — e.g. "CLI tools
for web pentest / CVE enumeration / exploitation", "best X tools in 2026", "list of
tools for Y".

## The listicle trap
- The Tiny Fish corpus for these queries is almost always **listicle-dominated**:
  blog roundups ("top-N tools in 2026", "7 tools you must know"), forum threads,
  YouTube videos, plus a few authoritative anchors (github `awesome-*` lists, OWASP).
- Phases 1–3 give you the *corpus*, not the *answer*. For a "list of tools" question,
  the answer must be **assembled by the agent**, not concatenated from sources.
- Do NOT merge raw scraped sources. This is a curated-extraction task.

## Extraction recipe (Python)
`research_data.json` → `d['all_items']` = list of `{title, content, url}`. `content`
includes the full scraped page.

```python
import json
d = json.load(open('research_data.json'))
blob = lambda i: (i['title'] + ' ' + i['content']).lower()
hits = {}
for token in ['nmap','nikto','sqlmap','gobuster','ffuf','feroxbuster','wfuzz','wpscan',
              'acunetix','nessus','openvas','metasploit','hydra','medusa','nuclei',
              'amass','subfinder','assetfinder','httpx','theharvester','sublist3r',
              'dnsrecon','dnsenum','crt','paramspider','whatweb','wafw00f','dirb']:
    for i in d['all_items']:
        if token in blob(i):
            hits.setdefault(token, []).append(i['url'])
```
- Match **lowercase** tokens against title+content; collect source URLs to cite.
- Group hits into buckets: reconnaissance/enum · web-app testing · exploitation · cred brute-force.
- `set()`-dedupe URLs before citing.

## Curate, don't concatenate
- Deliver as grouped tables, ranked by post-count (post-count = strongest consensus).
- Flag LLM-agent pentest tools (RapidPen-style) as a separate *emerging* cluster.
- Include the legal-scope caveat — these are offensive tools requiring authorization.

## Deliverable decision
- User said "just summarize" / gave a summary intent → category summary table (deliver now;
  the full HTML report is optional).
- User wants a full report → follow the normal 4-phase report path.
