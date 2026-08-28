# Test Matrix Template

Template for generating comprehensive test matrices for software projects.
Used during QA analysis to map features → user journeys → test cases across all layers.

## Structure

A test matrix has two dimensions:
1. **Test layer** — unit, module, integration, E2E
2. **Surface** — API, UI (or other surfaces like CLI, database, etc.)

## Template

```markdown
# Test Matrix — <Project Name>

## Project Overview
- **Type:** (e.g., FastAPI + Next.js, Django + React, etc.)
- **Key features:** (bullet list)
- **User journeys:** (numbered list)

## API Test Matrix

### Unit Tests
| # | Feature | Test Case | Expected | Layer |
|---|---------|-----------|----------|-------|
| 1 | ... | ... | ... | unit |

### Module Tests
| # | Module | Test Case | Expected | Layer |
|---|--------|-----------|----------|-------|

### Integration Tests
| # | Feature | Test Case | Expected | Layer |
|---|---------|-----------|----------|-------|

### E2E Tests
| # | User Journey | Test Case | Expected | Layer |
|---|--------------|-----------|----------|-------|

## UI Test Matrix

### Unit Tests
| # | Component | Test Case | Expected | Layer |
|---|-----------|-----------|----------|-------|

### Module Tests
| # | Module | Test Case | Expected | Layer |
|---|--------|-----------|----------|-------|

### Integration Tests
| # | Feature | Test Case | Expected | Layer |
|---|---------|-----------|----------|-------|

### E2E Tests
| # | User Journey | Test Case | Expected | Layer |
|---|--------------|-----------|----------|-------|

## Bug Documentation
| # | Bug | Severity | Test That Documents It |
|---|-----|----------|----------------------|
```

## How to Use

1. **Read the codebase** — Understand all features and user journeys
2. **Map features to test layers** — For each feature, determine which layers need testing
3. **Fill in the matrix** — Use the table format above
4. **Run existing tests** — Verify current test coverage
5. **Identify gaps** — Compare matrix against existing tests
6. **Document bugs** — Any test failure that reveals a bug goes in the bug table
7. **Generate test files** — Create actual test files from the matrix

## Key Principles

- **Every feature needs at least one test** at some layer
- **Edge cases matter** — empty input, large payloads, malformed data, concurrent requests
- **Bug documentation in tests** — When a test reveals a bug, document it with a BUG comment
- **Auth middleware ordering** — In FastAPI, auth runs before validation (401 before 422)
- **Don't test what's already tested** — Check existing tests before creating duplicates
- **Test the surface, not the implementation** — Focus on user-facing behavior
