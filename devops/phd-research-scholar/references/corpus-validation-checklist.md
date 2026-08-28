# Corpus Validation Checklist

Noise patterns observed across document corpora. Use as a reference when auditing any document collection.

## Noise Patterns (DELETE)

| Pattern | Detection | Threshold | Example |
|---------|-----------|-----------|---------|
| CLI Command References | `cli\s+\d+\.\d+` in TITLE only | title match | `ec2 — AWS CLI 2.36.6 Command Reference` |
| SDK References | `sdk\s+for\s+(java|python|go|js)` in TITLE only | title match | `AWSServiceQuotasClient (AWS SDK for Java)` |
| Very Small Files | Total content <300 chars | <300 chars | stub pages, truncated downloads |
| Broken Headings | `# None` heading + short content | <1000 chars | `# None\n\n---\nSource: ...` |
| Welcome Stubs | `"Welcome -"` in TITLE + short | <1500 chars | `Welcome - Amazon Textract` |
| Glossary Entries | `"aws glossary"` in first 500 chars | content match | glossary term definitions |

### False Positive Warnings (KEEP these!)

The default `corpus_validate.py` classifier is over-aggressive. These are commonly mistaken for noise:

| File Type | Why It's Flagged | Why to Keep |
|-----------|-----------------|-------------|
| `"Welcome - Amazon S3"` (3.3KB) | "Welcome -" content match | Foundational service intro, architecture decisions reference it |
| `"What is Amazon DynamoDB?"` (15KB) | Content contains "Welcome" heading | Core service architecture doc, essential for RAG |
| `"Creating an Amazon SNS topic"` (22KB) | Content contains "Welcome" | Operational guidance with architecture details |
| AWS Well-Architected Framework (1.7MB) | Contains "aws cli" 31+ times | The single most important corpus file |
| IAM best practices (16KB) | Contains "aws cli" in passing | Key security architecture guidance |

## Quality Patterns (KEEP)

| Pattern | Description |
|---------|-------------|
| Best Practices | "Best practices" with architecture guidance |
| Well-Architected | AWS Well-Architected Framework pillar guidance |
| Service Architecture | Service-specific architecture patterns |
| Lens Documentation | Workload lens recommendations |
| Migration Guidance | Migration strategies and patterns |
| Operational Guidance | Operating and monitoring docs |

## Classification Workflow

1. **Backup** → `cp -r corpus corpus.corpus_backup.<date>/`
2. **Scan** → Total files, size stats, first-line titles
3. **Noise detection** → Regex/pattern matching on content
4. **Pillar classification** → Keyword scoring per AWS Well-Architected pillar
5. **Service cross-ref** → Multiple AWS services per file
6. **Output** → Report, new category_index, manifest, deletion scripts
7. **Verify** → `unique pillar files == total kept files`

## Key Metrics to Report

- Total files (before cleanup)
- Valid files (after noise removal)
- Deleted noise (count, breakdown by type)
- Pillar distribution (per-pillar quality coverage)
- Service distribution (top services by coverage)
- Uncategorized count (needs manual review)
- Duplicate count (should be 0)
