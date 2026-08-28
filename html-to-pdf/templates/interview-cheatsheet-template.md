---
name: interview-cheatsheet
description: HTML template structure for interview prep cheat sheets. Each section has: usage block, code example with syntax highlighting, and 2 practice problems with hints. Designed for HTML-to-PDF conversion with WeasyPrint.
tags: [html, pdf, interview, cheatsheet, template]
---

# Interview Cheat Sheet HTML Template Structure

Use this structure when building interview preparation cheat sheets from code examples to printable PDFs via WeasyPrint.

## Section Template

Every section follows the same 3-part pattern:

1. **Usage Block** — `<div class="usage">` with context on why this topic matters
2. **Code Example** — `<div class="code-block">` with syntax-highlighted Python code
3. **Practice Problems** — `<div class="problems">` with 2 problems + hints

## HTML Skeleton

```html
<div class="section">
  <div class="section-header">
    <div class="section-number">NN</div>
    <h2>Topic Name</h2>
  </div>
  <div class="usage">
    <strong>Usage:</strong> Brief explanation of why this matters and when to use it.
  </div>
  <div class="code-block">
<span class="code-comment"># Comment</span>
<span class="code-keyword">def</span> <span class="code-func">example</span>():
    <span class="code-keyword">pass</span>
  </div>
  <div class="problems">
    <h4>🧩 Practice Problems</h4>
    <div class="problem">
      <h5>Problem 1</h5>
      <p>Problem description text.</p>
      <p class="hint">💡 Hint: What to focus on</p>
    </div>
    <div class="problem">
      <h5>Problem 2</h5>
      <p>Problem description text.</p>
      <p class="hint">💡 Hint: What to focus on</p>
    </div>
  </div>
</div>
```

## CSS Classes for Syntax Highlighting

| Class | Color Purpose |
|-------|---------------|
| `.code-keyword` | `def`, `class`, `import`, `return`, `if`, `for`, `in`, `with`, `try`, `except`, `yield` |
| `.code-string` | String literals (`"..."`, `'...'`, f-strings) |
| `.code-comment` | `# comments` (italic, muted color) |
| `.code-func` | Function names |
| `.code-num` | Number literals |

## Interview Question Integration

When converting interview questions into practice problems:
- Phrase as a technical challenge, not a Q&A
- Include the domain context (e.g., "StorageGRID node health check")
- Provide a 💡 hint that points to the key technique, not the answer
- Keep each problem self-contained with no external dependencies

## Topics to Cover (Progressive Difficulty)

**Basic:** Variables, Control Flow, Functions, Collections, Strings
**Intermediate:** File I/O, Error Handling, OOP, Comprehensions, Iterators, Decorators, Modules
**Advanced:** Concurrency, pytest, API Testing, Profiling, Logging, Distributed Systems
**Role-Specific:** S3 Testing, System Testing, CI/CD, Load Testing, Chaos Testing, RCA, Framework Architecture
