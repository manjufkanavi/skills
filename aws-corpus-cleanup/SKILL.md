---
name: aws-corpus-cleanup
description: Automated corpus evaluation and cleanup for AWS documentation RAG datasets. Classifies .md files into KEEP/DELETE/UNCERTAIN based on RAG relevance for cloud architecture decision support.
version: 1.0.0
tags: [corpus, RAG, AWS, data-cleaning, classification]
---

# AWS Corpus Cleanup — RAG-Relevance Classification

Systematic evaluation of AWS documentation corpora for RAG/fine-tuning relevance. Used by Solvarch project.

## When to Use
- You have a corpus of scraped/crawled AWS docs (markdown format) and need to filter for RAG relevance
- Before fine-tuning: remove noise that would degrade model quality
- After corpus collection: prune irrelevant content before building the retrieval index

## Classification Criteria

### DELETE (definitely remove)
| Pattern | Reason |
|---------|--------|
| AWS CLI command references | Boring API docs, zero architecture insight |
| AWS Certification exam prep | Not relevant to architecture decisions |
| AWS Glossary pages | Low value for RAG fine-tuning |
| SDK/Boto3/Java references | Code docs, not architecture |
| Document history pages | Metadata only |
| Non-English content | Chinese, Spanish (English corpus) |
| GitHub issues/discussions | Not authoritative docs |
| Tiny navigation stubs | <300 chars |
| Service "Welcome" pages | Minimal intros, no architecture detail |

### KEEP (definitely keep)
| Content Type | Examples |
|-------------|----------|
| Well-Architected Framework | All 6 pillar docs |
| ADRs | Architecture Decision Records |
| Prescriptive Guidance | AWS best practices, patterns |
| Security | IAM, KMS, GuardDuty, WAF, SRA |
| Cost Optimization | Savings Plans, Reserved Instances |
| Migration | Migration services, landing zones |
| Organizations | Multi-account, Control Tower |
| Industry Lenses | Financial Services, SAP, etc. |
| IaC | Terraform, CloudFormation, CDK |
| Compute | Lambda, EC2, ECS, EKS, Fargate |
| Storage | S3, EBS, EFS |
| Networking | VPC, Route 53, CloudFront |
| Monitoring | CloudTrail, CloudWatch |
| Database | DynamoDB, RDS, Redshift |
| Serverless | API Gateway, Step Functions, App Runner |
| Disaster Recovery | DR patterns, Elastic Disaster Recovery |
| CAF | Cloud Adoption Framework |
| Architecture patterns | microservices, GitOps, CQRS, event-driven |

### UNCERTAIN (manual review)
- Files between 1000-3000 chars with 1-2 AWS service mentions
- GitHub ADR repos with >2000 bytes content
- Industry lens content that's mostly conceptual

## Execution Steps

1. **Backup**: `cp -r corpus/. .corpus_backup/` and add `.corpus_backup/` to `.gitignore`
2. **Classify**: Run classification script (see reference script below)
3. **Review uncertain**: Manual spot-check of UNCERTAIN files
4. **Delete**: Remove DELETE files
5. **Verify**: Count remaining files, check sizes
6. **Update README**: Reflect cleaned corpus stats
7. **Commit**: `git add -A && git commit -m "corpus: clean irrelevant files (N deleted, M kept)"`
8. **Push**: `git push origin main`

## Reference Script

```python
#!/usr/bin/env python3
"""AWS corpus classification — KEEP/DELETE/UNCERTAIN for RAG relevance."""

import os
from pathlib import Path

CORPUS_DIR = Path("path/to/corpus")

KEEP_PATTERNS = [
    "Well-Architected", "Architecture Decision Record", "Security Reference",
    "Disaster Recovery", "AWS Organizations", "Control Tower",
    "Cost Optimization", "Savings Plans", "Reserved Instances",
    "Migration", "landing zone", "multi-account", "Multi-Region",
    "Prescriptive Guidance", "best practices", "Best Practices",
    "Lens", "CAF", "Cloud Adoption Framework", "Terraform",
    "Lambda", "ECS", "EKS", "DynamoDB", "RDS", "IAM", "VPC",
    "CloudTrail", "CloudWatch", "Route 53", "CloudFront", "S3",
    "EBS", "EFS", "KMS", "GuardDuty", "WAF", "Config",
    "microservices", "GitOps", "Serverless", "micro-frontend",
]

DELETE_PATTERNS = [
    "AWS CLI", "AWS Command Line Interface", "AWS Certification",
    "certified-", "AWS Glossary", "API Reference - Amazon",
    "Chime - Boto3", "Boto3", "AWS SDK for", "Class: Aws::",
]

NON_ENGLISH = ["最终用户", "Familia de productos"]

for f in sorted(CORPUS_DIR.glob("*.md")):
    size = os.path.getsize(f)
    with open(f) as fh:
        content = fh.read()
        title = content.split("\n")[0].strip()
    
    # Delete: non-English
    for pat in NON_ENGLISH:
        if pat in content: ...
    
    # Delete: known patterns
    for pat in DELETE_PATTERNS:
        if pat in title or pat in content[:200]: ...
    
    # Delete: tiny
    if size < 300: ...
    
    # Keep: patterns match
    for pat in KEEP_PATTERNS:
        if pat in title or pat in content[:500]: ...
```

## Pitfalls
- **False positives**: Some AWS glossary files are large and useful — check size before deleting by pattern alone
- **Document history**: CloudTrail/doc-history files contain service evolution info — spot-check before bulk delete
- **Welcome pages**: Some have good architectural intros — only delete if <1500 chars
- **GitHub ADRs**: Can be useful references — keep if >2000 bytes and architecture-focused
- **Always backup first**: The `.corpus_backup` step is non-negotiable
