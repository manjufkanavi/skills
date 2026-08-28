# TDD Patterns (from original test-driven-development skill)

## RED-GREEN-REFACTOR

1. **RED** — Write a failing test expressing desired behavior
2. **GREEN** — Write minimal code to pass the test
3. **REFACTOR** — Clean up with test suite as safety net
4. Repeat

## Pitfalls
- Tests must be fast (< 1s)
- If you can't write a failing test, the requirement isn't clear
- Don't write too many tests at once — one at a time
- Refactoring must be driven by test suite passing
