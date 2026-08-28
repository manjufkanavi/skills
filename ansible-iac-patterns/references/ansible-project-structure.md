# Ansible Project Structure

## Complete Directory Tree

```
iacgenie-ansible/                          # Root project directory
├── ansible.cfg                            # Ansible configuration
├── inventory/                             # Multi-environment inventory
│   ├── hosts.ini                          # Static inventory
│   ├── group_vars/
│   │   ├── all.yml                        # Variables for ALL environments
│   │   ├── webservers.yml                # Nginx-specific vars
│   │   ├── databases.yml                 # Postgres/Redis vars
│   │   ├── microservices.yml             # App container vars
│   │   └── tunnels.yml                   # Cloudflare Tunnel vars
│   ├── dev/                              # Dev environment overrides
│   ├── staging/                          # Staging environment overrides
│   └── prod/                             # Production environment overrides
├── host_vars/
│   └── iacgenie-server.yml              # Host-specific: IP, RAM, disk, hostname
├── playbooks/                            # Playbook entry points
│   ├── site.yml                         # Master: orchestrates ALL roles
│   ├── bootstrap.yml                    # First-time: OS hardening, Docker
│   ├── services.yml                     # Deploy all Docker services
│   ├── validate.yml                     # Health checks post-deployment
│   ├── backup.yml                       # Full backup orchestration
│   └── restore.yml                      # Point-in-time restore
├── roles/                                # Ansible roles (one per service)
│   ├── common/                          # Base OS hardening
│   ├── docker/                          # Docker CE + compose plugin
│   ├── postgresql/                      # PostgreSQL 15
│   ├── redis/                           # Redis 7
│   ├── minio/                           # MinIO object storage
│   ├── openbao/                         # OpenBao secrets management
│   ├── keycloak/                        # Keycloak 26
│   ├── gitea/                           # Gitea Git service
│   ├── lightserp/                       # LightSerp API + WebUI
│   ├── searxng/                         # SearXNG search
│   ├── nsqd/                            # NSQD message queue
│   ├── pagezen/                         # PageZen crawler
│   ├── nginx/                           # Nginx reverse proxy
│   ├── cloudflare_tunnel/               # Cloudflare Tunnel
│   ├── docker-compose-generator/        # Renders all compose files
│   ├── backup/                          # Multi-service backup orchestration
│   └── monitoring/                      # Prometheus + Grafana
├── ansible-vault/                       # Encrypted secrets
├── scripts/                             # Supporting scripts
├── .github/workflows/                   # CI/CD
├── .ansible-lint                        # Lint configuration
├── Makefile                             # Common commands
└── README.md                            # Project documentation
```

## Key Design Decisions

1. **`site.yml` is an orchestrator only** — imports/role-calls roles in order. No business logic.
2. **One role per service** — Each role is independently runnable.
3. **All configs as Jinja2 templates** — No raw files copied. Everything is parameterized.
4. **`docker-compose-generator` role** — Renders master compose from fragments.
5. **Environment isolation** — `dev/`, `staging/`, `prod/` directories override variables.
6. **Secrets in Ansible Vault** — Never in plain text.
7. **Makefile for CLI** — `make bootstrap`, `make deploy`, `make validate` provide simple interface.