---
name: kannada-essay
description: Agy-powered Kannada essay generation — uses agy CLI with role-based prompting to produce high-quality Kannada essays on any topic.
tags: [kannada, essay, antigravity, agy, writing]
---

# Kannada Essay — Agy-Powered Essay Generator

## Overview

Generates a polished Kannada essay on any topic using agy (Antigravity CLI) with a structured **role + prompt** system. The agy agent takes on the persona of a renowned Kannada essayist, producing a well-structured essay with introduction, body paragraphs, and conclusion.

### How It Works

1. **Topic** → You provide a topic (in Kannada or English)
2. **Role Assignment** → agy is given a specific role (e.g., "ಪ್ರಖ್ಯಾತ ಕನ್ನಡ ಪ್ರಬಂಧಕಾರ" — Renowned Kannada Essayist)
3. **Structured Prompt** → The prompt specifies format, tone, length, and focus areas
4. **agy generates** → agy writes the full essay with Kannada title, byline, introduction, thematic sections, and conclusion
5. **Saved** → Output saved as a `.md` file in `essays/<topic_slug>.md`

## Quick Start

```bash
python3 skills/kannada-essay/main.py --topic "ಪ್ರೀತಿ ಮತ್ತು ಆಧ್ಯಾತ್ಮಿಕತೆ"
```

Or with an English topic (agy will write in Kannada):

```bash
python3 skills/kannada-essay/main.py --topic "Love and Spirituality in Modern Times" --style philosophical
```

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--topic` | Essay topic (Kannada or English) | Required |
| `--role` | agy agent role override | *Default essayist role* |
| `--style` | Essay style: philosophical, analytical, descriptive, narrative, reflective | philosophical |
| `--length` | Target word count (~500 = 3min read) | 500 |
| `--model` | agy model to use | "gemini-3.1-pro-high" |
| `--effort` | agy reasoning effort (low, medium, high) | high |
| `--output` | Output directory | `essays/` |
| `--force` | Re-generate if file exists | False |

## Model Notes

- Uses **Gemini 3.1 Pro** with **high reasoning effort** for deeper thinking via `<think>` tags.
- The model deliberately thinks through the topic before writing, considering cultural, spiritual, and philosophical dimensions.

## Output

```
essays/
  preeti_matthu_aadhyatmikate.md    — Markdown essay with full Kannada content
```

## Default Role (used when `--role` is not specified)

> ನಿಮ್ಮ ಪಾತ್ರ: ಪ್ರಖ್ಯಾತ ಕನ್ನಡ ಪ್ರಬಂಧಕಾರ. ನೀವು ಕನ್ನಡ ಸಾಹಿತ್ಯದಲ್ಲಿ ಆಳವಾದ ಪಾಂಡಿತ್ಯವನ್ನು ಹೊಂದಿದ್ದೀರಿ. ನಿಮ್ಮ ಬರಹಗಳು ಸರಳ, ಸುಂದರ ಮತ್ತು ಅರ್ಥಪೂರ್ಣವಾಗಿರುತ್ತವೆ. ನೀವು ಸಂಕೀರ್ಣ ವಿಚಾರಗಳನ್ನು ಸಹ ಸಾಮಾನ್ಯ ಓದುಗರಿಗೆ ಸುಲಭವಾಗಿ ಅರ್ಥವಾಗುವಂತೆ ವಿವರಿಸಬಲ್ಲಿರಿ.

(You are a renowned Kannada essayist with deep scholarship in Kannada literature. Your writing is simple, beautiful, and meaningful. You can explain complex ideas in a way that ordinary readers can easily understand.)

## agy Usage Rules

See `kannada-poet-agy/SKILL.md` for agy CLI conventions.

1. Never use `-p` with shell inline single quotes for long prompts — use stdin piping via Python subprocess.
2. agy wraps output in plain text, not JSON — response is used directly as the essay content.
3. Timeouts — agy can take 30-180 seconds for essay generation. Default timeout is 300s.

## Prerequisites

- `agy` CLI installed and authenticated (`agy agents`)
- Workspace path: `~/.nanobot/workspace`

## File Location

**Working copy:** `~/.nanobot/workspace/skills/kannada-essay/main.py`
