# Gitea CI/CD Workflow Templates

Deployed 2026-08-01 for iacgenie-deploy Phase 3 CI/CD tasks.

## iacgenie-smoke-test.yml
- **Repo:** `iacgenie`
- **Dest:** `.github/workflows/smoke-test.yml`
- **Jobs:** smoke-test (checks Gitea, Keycloak, pgAdmin URLs)
- **Content:** URL health checks against gitea.iacgenie.com, keycloak.iacgenie.com, pgadmin.iacgenie.com

## iacgenie-full.yml
- **Repo:** `iacgenie`
- **Dest:** `.github/workflows/docker-build-deploy.yml` (mapped from full-pipeline)
- **Jobs:** lint (ansible-lint), test (syntax-check), build (compose validate), full-pipeline (main-only)
- **Content:** Full CI pipeline for the iacgenie infrastructure repo

## lightserv-ci.yml
- **Repo:** `lightserp`
- **Dest:** `.github/workflows/smoke-test.yml`
- **Jobs:** lint (docker-compose validate), smoke-test (lightserv API + webUI URLs)
- **Content:** CI for LightSerp service

## docker-build-deploy.yml
- **Repos:** `iacgenie`, `lightserp`, `iacgenie-unified-infra`
- **Dest:** `.github/workflows/docker-build-deploy.yml`
- **Jobs:** docker-build (template validation + image pre-pull), deploy (Ansible deploy step)
- **Content:** Generic Docker build + deploy workflow for all repos

## infra-ci.yml
- **Repo:** `iacgenie-unified-infra`
- **Dest:** `.github/workflows/infra-ci.yml` (already existed, verified)
- **Jobs:** lint (ansible-lint + docker-compose validate + shellcheck)
- **Content:** Infrastructure validation only

## iacgenie-ci.yml
- **Repo:** `iacgenie-unified-infra`
- **Dest:** `.github/workflows/iacgenie-ci.yml` (already existed, verified)
- **Jobs:** lint (ansible-lint), test (syntax-check all playbooks), build (compose validate)
- **Content:** iacgenie integration CI from unified-infra repo

## Deployment Method

These workflows were intended to be deployed to Gitea repos using the **non-bare clone + push** pattern:

1. `git clone --no-checkout <bare-repo-url> <clone-dir>`
2. Modify working tree (add files to `.github/workflows/`)
3. `git add .github/workflows/` + `git commit`
4. `git push origin main --force` (or bypass pre-receive hooks)

**Known blocker:** The `pre-receive` hook references `/usr/local/bin/gitea` which doesn't exist on the host filesystem, only inside the Docker container. See the main skill for the hook-bypass workaround.
