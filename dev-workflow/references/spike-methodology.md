# Spike Methodology (from original spike skill)

## 5-step loop

```
decompose → research → build → verdict
   ↑__________________________________________↓
                  iterate on findings
```

## Step details

### 1. Decompose
Break the idea into 2-5 independent feasibility questions. Each is a spike.
Present as Given/When/Then table. Order by risk (most likely to kill runs first).

### 2. Align
Present spike table to user. Ask to confirm order.

### 3. Research
Brief each spike (2-3 sentences). Surface competing approaches. Pick one per spike.

### 4. Build
One directory per spike. Standalone. Bias toward interactive output (CLI > HTML > test).

### 5. Verdict
VALIDATED / PARTIAL / INVALIDATED. Document: what worked, what didn't, surprises, recommendations.

## Parallel comparison spikes (002a / 002b)
Use `delegate_task` batch mode for variants that can run concurrently.

## Pitfalls
- Spikes are disposable — don't over-engineer the prototype
- Depth over speed — test edge cases
- Avoid complex package management, build tools, Docker in spikes
