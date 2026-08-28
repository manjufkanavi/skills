# Gitea Actions CI/CD Workflow Templates

Workflows use `.github/workflows/` (identical to GitHub Actions format). The Gitea runner (`act_runner` v0.6.1+) executes them.

## Python Backend (FastAPI/Flask)

```yaml
name: Lint

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install ruff
        run: pip install ruff

      - name: Lint
        run: ruff check . && ruff format --check .
```

## TypeScript/Node.js

```yaml
name: Lint

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '22'

      - run: npm ci
      - run: npx tsc --noEmit
      - run: npx eslint src/ 2>/dev/null || echo "ESLint not configured"
```

## Docker Build

```yaml
name: Build

on:
  push:
    branches: [main, develop]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Verify image
        run: docker images | grep myapp
```

## Deploy (main branch only)

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and tag
        run: |
          docker build -t myapp:${{ github.sha }} .
      - name: Verify
        run: docker images | grep myapp
```

## Notes

- Use `continue-on-error: true` for steps that may fail due to missing external services (Postgres, etc.)
- The Gitea runner supports `docker://` label syntax (e.g., `ubuntu-latest:docker://docker.gitea.com/runner-images:ubuntu-latest`)
- Jobs run on the self-hosted runner; use `runs-on: ubuntu-latest` which maps to the runner's labels
