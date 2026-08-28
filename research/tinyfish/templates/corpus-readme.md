# {{corpus_name}} Domain Corpus

**Fetched:** {{date}}  
**Total documents:** {{total_docs}}  
**Total size:** {{total_mb}} MB  
**Format:** Markdown (one file per document)

## Scope

{{scope_description}}

## Structure

```
{{corpus_dir}}/
├── manifest.json       # Full manifest with categories and file index
├── category_index.json # Documents grouped by category
├── collected_urls.json # List of all URLs fetched
├── README.md           # This file
├── <hash>.md           # Individual document files
└── ...
```

## Cleaning

All documents were cleaned:
- Removed common navigation footers and "Was this page helpful?" blocks
- Deduplicated repeated breadcrumb/navigation lines
- Skipped PDF files and binary content
- Minimum content threshold: {{min_chars}} characters
- Markdown format from {{fetcher}} API

## Generation

Generated using:
1. {{num_queries}} search queries targeting {{target_sites}}
2. URLs fetched {{fetch_strategy}}
3. PDFs and empty content filtered out
4. Content cleaned and deduplicated

## Categories

| Category | Count |
|----------|-------|
{{categories_table}}

## Usage

{{usage_notes}}
