# Nightly Test Results JSON Format

Standard structure for test result reports saved to `~/.hermes/shared/test_results/`.

## Structure

```json
{
  "timestamp": "ISO-8601",
  "job": "nightly_test_suite",
  "run_id": "cron-YYYYMMDD-HHMM",
  "projects": {
    "ProjectName": {
      "type": "pytest|npm|cargo|planning",
      "status": "pass|fail|skip",
      "tests_run": N,
      "passed": N,
      "failed": N,
      "errors": N,
      "skipped": N,
      "duration": "string (e.g. '15.13s')",
      "notes": "optional context (import issues, missing deps, no scripts)"
    }
  },
  "summary": {
    "total_projects": N,
    "passed": N,
    "failed": N,
    "skipped": N,
    "pass_rate": "XX.X%"
  }
}
```

## Status Classification

| Status | Meaning |
|--------|---------|
| pass | Tests ran, all passed (or no tests ran with no errors) |
| fail | Tests ran and failed, or collection/compilation/import errors |
| skip | No test infrastructure (no test script, no code, planning stage) |
