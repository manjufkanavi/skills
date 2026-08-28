---
name: coding-agents
description: "Client wrappers for AI coding tools — Claude Code CLI, OpenAI Codex CLI, and OpenCode CLI. Configure, use, and troubleshoot each agent."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Claude-Code, Codex, OpenCode, AI-coding, coding-agent, CLI]
---

# AI Coding Agents — Complete Reference

Client wrappers for the major AI coding tools. Configure, use, and troubleshoot Claude Code, Codex, and OpenCode.

## Contents

| Section | Description |
|---------|-------------|
| [1. Claude Code](#1-claude-code) | Claude Code CLI: features, PRs, delegation |
| [2. Codex](#2-codex) | OpenAI Codex CLI: features, PRs, delegation |
| [3. OpenCode](#3-opencode) | OpenCode CLI: features, PR review |

---

## 1. Claude Code

### Basics

```bash
# Install
npm install -g @anthropic-ai/claude-code

# Basic usage
claude "write a function that sorts an array"

# With file context
claude src/main.py

# Preview changes (no write)
claude --preview "refactor this function"

# Dry run
claude --dry-run "add error handling"

# Stream mode
claude --stream "implement feature X"

# Rich mode
claude --rich
```

### Advanced Usage

```bash
# Bash integration (scriptable)
claude -p "command"

# Chat mode
claude --client chat

# Browser integration
claude --chrome "test this page"
```

### Key Features

- **Dry run** (`--dry-run`): Preview changes without writing
- **Preview** (`--preview`): Show diff before committing
- **Stream** (`--stream`): Real-time token output
- **Rich** (`--rich`): Use the structured output protocol
- **Client** (`--client chat`): Interactive chat mode
- **Bash** (`-p`): Pipe-based for scripting

### Pitfalls

- Command must be at the **end** of the invocation: `claude --stream "message"`
- Path args come **before** the message: `claude src/main.py "refactor this"`
- Pass file paths as separate args: `claude file1.py file2.py "message"`
- You can't pass args twice: `claude --dry-run --dry-run "msg"` is wrong
- Write mode is inferred from the message, not flags
- Use `--rich` for structured output (parseable JSON)

---

## 2. Codex

### Setup

```bash
# Install
pip install openai-codex-cli

# Configure
codex init
```

### Basic Usage

```bash
# Run on file
codex src/main.py

# Run with slash commands
codex -c "/scope" src/main.py

# Dry run
codex --dry-run "refactor this"
```

### Slash Commands

| Command | Description |
|---------|-------------|
| `/scope` | Scope current context |
| `/reset` | Reset the agent context |
| `/status` | Current status |
| `/agents` | Manage agents |

### Pitfalls

- You need an OpenAI API key with Codex access
- Codex has its own project management system

---

## 3. OpenCode

### Basic Usage

```bash
# Review a PR
opencode review 123

# Generate code
opencode "write a function to sort"

# Interactive mode
opencode
```

### Features

- PR review with inline comments
- Code generation from descriptions
- Interactive mode for iterative refinement

---

## Comparison

| Feature | Claude Code | Codex | OpenCode |
|---------|-----------|-------|----------|
| Dry run | `--dry-run` | `--dry-run` | N/A |
| Stream mode | `--stream` | N/A | N/A |
| Preview mode | `--preview` | N/A | N/A |
| Rich output | `--rich` | N/A | N/A |
| Browser | `--chrome` | N/A | N/A |
| Language | Node.js | Python | N/A |
| Vendor | Anthropic | OpenAI | N/A |
