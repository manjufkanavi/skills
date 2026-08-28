# Google Dorks for Finding Reference Material PDFs

Use these dork patterns with Tiny Fish search (or any search engine) to find authoritative cheat sheets, guides, and reference PDFs.

## General PDF Search Dorks

| Dork Pattern | What It Finds |
|---|---|
| `"topic" filetype:pdf` | Direct PDF results for the topic |
| `"topic cheat sheet" filetype:pdf` | Cheat sheet PDFs |
| `"topic" site:github.com filetype:pdf` | GitHub-hosted PDFs |
| `"topic" site:edu filetype:pdf` | Academic/educational PDFs |
| `"topic tutorial OR guide OR reference" filetype:pdf` | Tutorial/guide PDFs |
| `interview "topic cheat sheet" filetype:pdf` | Interview-focused PDFs |

## GitHub-Specific Dorks

| Dork Pattern | What It Finds |
|---|---|
| `site:github.com "*-cheat-sheet" filetype:pdf` | Dedicated cheat sheet repos |
| `site:raw.githubusercontent.com "*-cheat-sheet*.pdf"` | Raw PDF files in repos |
| `site:github.com "*reference" filetype:pdf` | Reference documents |

## Example Queries

```python
QUERIES = [
    'site:github.com "python cheat sheet" filetype:pdf',
    '"python cheat sheet" filetype:pdf',
    '"python programming" cheat sheet OR tutorial filetype:pdf',
    'interview "python cheat sheet" filetype:pdf',
]
```

## Source Quality Signals

**Prefer:**
- .edu — universities (well-structured course materials)
- github.com — open source communities (frequently updated)
- Established tech sites — Real Python, DataCamp, TutorialsPoint
- Corporate blogs — Snyk, Google Devs

**Avoid:**
- Random URLs (SEO spam)
- PDFs under 1KB (likely empty/redirect)
- Outdated Python 2.x materials

## Related Skills

- **tinyfish** — Web search and page fetching
- **html-to-pdf** — Alternative PDF generation on macOS