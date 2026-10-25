# iacgenie-platform — Condensed Knowledge Bank

Full detail: repo `iacgenie-platform/` at `~/.hermes/git_clone_dir/iacgenie-platform`. A unified monorepo for two products sharing one VM (192.168.0.118), deployed via Docker Compose, provisioned by Ansible.

## Layout (class-level map)
- `platform/` — IaCGenie application code.
  - `backend/` (~62K LOC Python) — FastAPI + Celery, Gemini-driven IaC generation.
  - `frontend/` (~5K LOC TSX) — React + Vite dashboard.
  - `infra/` — Terraform modules (main.tf, variables.tf, outputs.tf).
- `lightserv/` — LightSerp service (~6.4K LOC TypeScript) + Next.js WebUI.
- `infra/` — Shared infra: docker-compose, ansible roles (nginx/docker-services/openbao/grafana/resume-platform), nginx vhosts, systemd units, configs (prometheus/loki/grafana/cloudflared), scripts.
- `scripts/deploy.sh` — unified deploy (`--group iacgenie|lightsrp|all`, `--backup`, `--validate`).
- `shared/docs/ARCHITECTURE.md` — intended-design doc (treat as hypothesis, verify against code).

## IaCGenie backend architecture
- **Entry**: `platform/backend/main.py`, `start.py` — app factory (`app_factory.py`).
- **Core = Agentic Pipeline** (`pipeline/pipeline_engine.py` class `AgenticPipeline`): phase-driven orchestrator routing through agents mapped in `_initialize_phase_handlers()`:
  - `PipelinePhase.CLARIFY` → ClarifyAgent (asks user questions to nail intent)
  - `PipelinePhase.GENERATE` → GeneratorAgent (writes IaC: OpenTofu/Docker/K8s)
  - `PipelinePhase.FORMAT/INIT/VALIDATE` → CommandAgentFactory (FORMAT, INIT, VALIDATE)
  - `PipelinePhase.STATIC_ANALYSIS` → StaticAnalysisAgent (plan review / error classification)
  - `PipelinePhase.PLAN_REVIEW` → command agent (plan review gate before apply)
  - `PipelinePhase.APPLY` → ApplyAgent (**human-in-the-loop** gate before apply)
  - `PipelinePhase.CI` → CIAgent, plus GitAgent for git integration.
- **Agents** (`agents/`): base_agent.py, clarify_agent.py, generator_agent.py, static_analysis_agent.py, apply_agent.py, ci_agent.py, git_agent.py, command_agents.py (CommandType factory).
- **Models** (`models/`): multi-model registry — gemini.py, claude.py, mistral.py, ollama.py, openai.py, custom.py + registry.py. Domain models in `models/domain/`.
- **Modules** (`modules/`): workflow_engine, llm_proxy (multi-model), artifact_store, git_cicd, secret_store (OpenBao), observability.py, agent_executor.
- **Routers** (`routers/`): auth.py, code.py, projects.py, generations.py, pipeline.py, ws_pipeline.py (WebSocket live logs), api_keys.py, cloud_credentials.py, team_members.py, secrets.py, webhooks.py, audit_logs.py, metrics.py.
- **Services** (`services/`): auth_service.py, oauth_service.py, saml_service.py, ai_service.py, alerting_service.py, business_metrics_service.py, download_service.py, email_service.py/smtp2go_email_service.py, error_classifier.py, health_service.py, metrics_service.py, notification_service.py, webhook_service.py.
- **DB**: PostgreSQL via Alembic (alembic.ini + migrations/); SQLite fallback. `models/iac_state.py` = IaCState.
- **Auth**: Keycloak JWT (python-jose) + SAML/OAuth, shared-secret internal header for `/internal/` endpoints (bypasses auth-wrapper).

## IaCGenie agentic pipeline internals (deep-dive learnings)

Durable, reusable mechanics — read before writing to or reasoning about the pipeline.

- **IaCState** (`models/iac_state.py`, Pydantic) is the single source of truth threaded through every agent. Key fields: `session_id`, `user_request`, `refined_spec` (JSON from clarify), `hcl_code`, `work_dir`, `current_phase` (starts CLARIFY), `retry_counts`, `approvals` (`plan_approved` etc.), `clarification_history`. Supports `.checkpoint()` / `restore_from_checkpoint()` for resumability across process restarts (LangGraph MemorySaver).
- **Error-classification drives phase routing.** `BaseAgent.handle_error()` maps exceptions to an `ErrorClass` (RETRYABLE / CLARIFICATION / HUMAN_REQUIRED / FATAL) which selects the next phase. Default classification by exception name: `Timeout`/`Connection` → RETRYABLE, `Validation`/`Syntax` → CLARIFICATION, `Permission`/`Access` → HUMAN_REQUIRED, else FATAL. Agents can override for finer control — check this when a phase transition looks wrong.
- **ClarifyAgent prompting pattern (reusable).** Forces the LLM to output a single PURE JSON object with keys `thinking`, `total_questions_estimated`, `message`, `options` (2-4 concrete choices each with `label`/`value`/`description`, trade-offs), and `is_complete`. Rules baked in: exactly one targeted technical question at a time, NEVER vague ("give more details"), ALWAYS provide options with concrete values (e.g. `t3.medium`, `gp3 SSD`), and only set `is_complete: true` once an architectural checklist (compute/networking/storage/security/HA) is covered. System prompt lives in `agents/clarify_agent.py` — structured-JSON-forcing is a pattern worth copying elsewhere.
- **GeneratorAgent** calls `ai_service.generate_infrastructure()` then validates output via `tofu fmt -check` (falls back to a basic brace check if tofu is absent). Short-circuits: if `hcl_code` already exists and this isn't a retry, reuses it.
- **ApplyAgent safety.** Hashes the approved plan file, verifies `plan_approved`, checks drift before applying, attempts rollback on failure. No auto-apply without `approvals.plan_approved`.
- **CommandAgents** (`agents/command_agents.py`) execute real Terraform/OpenTofu commands via a `ContainerProvisioner`/`CommandExecutor`. **PITFALL — see sandbox note below.**
- **ModelRegistry** (`models/registry.py`) manages multiple providers with fallback chains, health caching (re-checks every 300s), and load balancing. Providers registered from env (`GEMINI_API_KEY`, `MISTRAL_API_KEY`+`DIRECT_MISTRAL_API_KEY`, `CLAUDE_API_KEY`, `OPENAI_API_KEY`). Each provider: base_url, model_name, max_tokens=8192, temperature=0.1, timeout=120s. **Supports BYOM** (custom + Ollama) — this is a multi-model platform, not Gemini-only.

## Gotcha: sandbox manager is stubbed in-repo
The `src/sandbox_manager/` package contains **stubs** (CommandExecutor, ContainerProvisioner, GarbageCollector, MTLSEnforcer all no-op). The real sandbox lives at an external `SANDBOX_MANAGER_URL` (default `http://127.0.0.1:8090`) provisioned by a separate process — NOT in this repo. When tracing how `tofu init/validate/plan/apply` actually executes, expect the real work to happen off-process; don't assume reading `command_agents.py` shows execution internals. Applying IaC therefore depends on an external sandbox service running separately from the FastAPI app.

## LightSerp architecture
- **Entry**: `src/server.ts`, HTTP server in `http-server.ts`. MCP interface for search.
- **Scrape subsystem**: scrape.ts, lightpanda-scrape.ts, pagezen.ts (browser scraping), parallel-scanner.ts.
- **Search**: search.ts; proxy support in proxy.ts; SSRF protection in ssrf.ts.
- **Async**: NSQ queue (queue.ts) for background scraping jobs; Redis cache (cache.ts).
- **Auth/security**: auth.ts, password-hashing.ts, secrets.ts.
- **Config**: searxng-settings.yml, prometheus.yml, grafana-datasources.yml.
- **Deployment**: docker-compose.yml / .prod.yml / .lightserp-web.yml, Dockerfile + Dockerfile.mcp.

## Shared infra stack (docker-compose-unified.yml services)
- **Data**: postgres, redis, minio (+minio-console), openbao.
- **Auth/identity**: keycloak, auth-wrapper (auth gateway).
- **Search/scrape**: searxng, pagezen.
- **Git/hosting**: gitea (3002).
- **Messaging/queue**: nsqd, n8n.
- **Observability**: prometheus (9090), loki, promtail, grafana.
- **Access layer**: cloudflared tunnel → Nginx vHost routing (all services bind 127.0.0.1 externally).
- **Security**: clamav-backend, crowdsec-backend.

## Deployment pattern (reusable)
- `./scripts/deploy.sh [--group <iacgenie|lightsrp|all>] [--backup] [--validate] [--dry-run]`.
- Flow: back up compose file → pull images → `docker compose -f infra/docker-compose/docker-compose-unified.yml up -d` → validate healthchecks.
- **Ansible is source of truth** for VM provisioning (roles in infra/ansible/). Convention: never edit deployed files directly — update Ansible templates, then redeploy.
- Bootstrap helpers: scripts/setup_keycloak_realm.py, deploy-secrets.py, fetch-openbao-env.py.

## Doc-vs-code gaps worth hunting (from the walkthrough)
- IaCGenie backend README still documents SQLite (`iacgenie.db`) as default DB — production uses PostgreSQL via Alembic. READMEs here lag reality; trust `alembic.ini` + migrations/ for the real schema.
- Backend README mentions MOCK_MODE and Gemini-only; code actually supports a multi-model registry (Gemini/Claude/Mistral/Ollama/OpenAI) — the models/ directory is newer than README.
- Frontend Dockerfile + nginx.conf are COPY-based (non-standalone Next.js build); CSS 404 is a known standalone-image bug.
- LightSerp package.json author field has a typo (`manjufkanavi` vs `mkanavi`) — cosmetic, ignore.
