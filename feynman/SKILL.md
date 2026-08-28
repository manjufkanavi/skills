---
name: feynman
description: "Apply the Feynman Technique for learning and reviewing any topic. Structured 4-step workflow: explain simply, identify gaps, review & simplify, and teach it to someone else. Supports one-shot natural language requests or step-by-step guided progress through each stage."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [feynman, learning, teaching, review, study, knowledge-management]
---

# Feynman Technique — Learn Anything Deeply

The Feynman Technique is a 4-step method for learning and reviewing any topic:

1. **Choose & Study** — Pick a concept, study it from books/papers/courses
2. **Explain Simply** — Teach it in plain language as if to a 12-year-old
3. **Identify Gaps** — Where your explanation breaks down, that's what you need to re-study
4. **Organize & Simplify** — Refine your explanation, use analogies, make it elegant

## How to Use This Skill

### One-shot review (most common)
```
/feynman [topic]
```
or just ask: "Teach me about [topic] using the Feynman Technique"

The agent will:
1. Explain the topic simply (step 2)
2. Identify common gaps/misconceptions (step 3)
3. Provide a refined summary with analogies (step 4)
4. Suggest a teaching exercise (step 4)

### Step-by-step mode (for deep mastery)
```
/feynman [topic] --step 1
/feynman [topic] --step 2
/feynman [topic] --step 3
/feynman [topic] --step 4
```

Each step pauses for user feedback before proceeding.

## The 4 Steps in Detail

### Step 1: Choose & Study
- State the concept clearly
- Gather source material (books, papers, notes)
- Focus on first-pass understanding

### Step 2: Explain Simply (THE CORE)
- Write an explanation as if teaching a **complete beginner**
- NO jargon, or if jargon is used, define it immediately
- Use simple sentences and everyday analogies
- If you can't explain it simply, you don't understand it well enough

### Step 3: Identify Gaps
- Where did you struggle in step 2?
- What parts did you hand-wave or use jargon to paper over?
- Go back to sources and re-study those specific areas
- This is where real learning happens

### Step 4: Organize & Simplify
- Rebuild your explanation from scratch
- Create a coherent narrative flow
- Use powerful analogies that illuminate the core idea
- If your explanation is still complex, simplify further

## Key Principles

- **Simplicity is the test of understanding** — if it's not simple, it's not understood
- **Gaps are features, not bugs** — finding what you don't know is the whole point
- **Analogies bridge the gap** between novice and expert understanding
- **Teaching is the ultimate test** — if someone else learned from your explanation, you've mastered it

## Examples

- `/feynman quantum entanglement` — Learn the basics of quantum entanglement
- `/feynman git merge conflicts` — Understand how git resolves merge conflicts
- `/feynman dynamic programming` — Master the concept of DP without heavy math
- `/feynman attention mechanism --step 2` — Just explain how attention works simply

## Pitfalls

- Don't skip to step 4 without completing steps 2 and 3 — that's just summarizing, not learning
- Don't use jargon in step 2 — if the concept REQUIRES jargon, define it in plain language first
- Don't assume you understand a concept just because you've read about it — the test is whether you can explain it simply

## See Also

- `references/course-workflow.md` — Workflow for applying the Feynman Technique to academic/course materials