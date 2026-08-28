# Pre-commit Review Checklist (from original requesting-code-review skill)

## Security Scan
- Hardcoded secrets, API keys, tokens
- SQL injection vectors
- XSS vectors (user input in HTML)
- Path traversal
- Auth bypass patterns

## Quality Gates
- Cyclomatic complexity
- Code duplication
- Dead code
- Unused imports/variables
- Error handling coverage

## Auto-fixes
- Remove hardcoded secrets → use env vars
- Fix common SQL injection → parameterized queries
- Remove dead code
