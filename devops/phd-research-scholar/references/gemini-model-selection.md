# Gemini Model Selection for Research Baselines

When selecting the most recent Gemini model for research baselines, use the agy CLI:

```bash
# List available models
agy models list

# Or check specifically for Gemini variants
agy models --filter gemini
```

## Preferred Models (as of 2026)

| Model | Notes |
|-------|-------|
| Gemini 2.5 Pro | Flagship, best for complex reasoning tasks |
| Gemini 2.5 Flash | Faster, cheaper, good for high-throughput evaluation |
| Gemini 2.0 Flash | Still relevant for cost-effective baselines |

## How to Use in Solvarch Evaluation

1. Pick the most recent Gemini model with API access
2. Use it alongside GPT-4/Claude as a frontier model baseline
3. Document exact model name (e.g., `gemini-2.5-pro-preview-06-05`)
4. Run same evaluation prompt template across all baseline models
5. Compare: Gemini vs GPT-4 vs Claude vs local Qwen2.5-Coder-3B

## Pitfalls

- Always use the exact model name from the API — version strings matter for reproducibility
- If no API access to Gemini, use local alternatives (Ollama, llama.cpp)
- Don't mix API providers without documenting cost/format differences in the evaluation report
