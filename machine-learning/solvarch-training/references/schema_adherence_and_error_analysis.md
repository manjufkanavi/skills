# Schema Adherence & Error Analysis Patterns

## Schema Adherence Test

Validates LLM outputs against the expected AWS architecture response schema.

### Required Sections (6 total)

| Section | Detection Keywords | Expected Rate |
|---------|-------------------|---------------|
| Overview | "overview", "architecture design", "architecture" | 100% |
| Services | "service", "configuration", "deployment" | 100% |
| Well-Architected | "well-architected", "pillar", "operational excellence", "security", "reliability", "performance efficiency", "cost optimization", "sustainability" | 95%+ |
| Data Flow | "data flow", "traffic flow", "request flow" | **85%+** (common gap) |
| Cost | "cost", "pricing", "estimate", "savings" | 85%+ |
| Security | "security", "encryption", "compliance", "iam" | 100% |

### Implementation

```python
def check_schema(response):
    resp_lower = response.lower()
    return {
        'has_overview': any(kw in resp_lower for kw in ['overview', 'architecture design', 'architecture']),
        'has_services': any(kw in resp_lower for kw in ['service', 'configuration', 'deployment']),
        'has_pillars': any(kw in resp_lower for kw in ['well-architected', 'pillar', 'operational excellence']),
        'has_data_flow': any(kw in resp_lower for kw in ['data flow', 'traffic flow', 'request flow']),
        'has_cost': any(kw in resp_lower for kw in ['cost', 'pricing', 'estimate', 'savings']),
        'has_security': any(kw in resp_lower for kw in ['security', 'encryption', 'compliance', 'iam']),
    }
```

### Common Findings

- **Data flow** is the most commonly missing section (75-100% of responses)
- **Cost** is the second most commonly missing (5-15% of responses)
- Fine-tuned models typically show slight improvement in schema compliance over base
- RAG-only models may have different section patterns due to retrieved context

## Error Analysis Patterns

### Error Types

| Error Type | Detection | Typical Rate |
|------------|-----------|--------------|
| `short_response` | Response length < 1000 chars | < 5% |
| `missing_sections` | One or more schema sections absent | 5-25% |
| `generic_template` | High density of generic keywords | 15-25% |
| `missing_required_services` | Required services from prompt not mentioned | 5-15% |

### Detection Logic

```python
def analyze_errors(sample):
    resp = sample['response']
    resp_lower = resp.lower()
    issues = []
    
    if len(resp) < 1000:
        issues.append('short_response')
    
    missing = []
    if 'overview' not in resp_lower and 'architecture' not in resp_lower:
        missing.append('overview')
    if 'well-architected' not in resp_lower and 'pillar' not in resp_lower:
        missing.append('well-architected')
    if 'cost' not in resp_lower and 'pricing' not in resp_lower:
        missing.append('cost')
    if 'security' not in resp_lower and 'encryption' not in resp_lower:
        missing.append('security')
    if 'data flow' not in resp_lower and 'traffic flow' not in resp_lower:
        missing.append('data_flow')
    if missing:
        issues.append(f'missing_sections:{",".join(missing)}')
    
    if resp_lower.count('service') > 10 and resp_lower.count('configuration') > 5:
        issues.append('generic_template')
    
    return issues
```

## Benchmark Comparison Framework

### Three-Way Comparison (Base vs RAG vs FT)

| Aspect | Base Model | RAG-Only | Fine-Tuned |
|--------|-----------|----------|------------|
| Loss | Baseline | Same as base | Improved |
| Perplexity | Baseline | Same as base | Improved |
| Service Coverage | Medium | **Highest** | Medium |
| Speed | **Fastest** | Medium | Slowest |
| Schema Compliance | Medium | Medium | **Best** |
| Context Grounding | Low | **Highest** | Medium |

### Key Insight

RAG-only outperforms fine-tuned on service coverage and speed. Fine-tuned excels at schema compliance and WA pillar alignment. A hybrid approach (RAG + FT) provides the best overall results.
