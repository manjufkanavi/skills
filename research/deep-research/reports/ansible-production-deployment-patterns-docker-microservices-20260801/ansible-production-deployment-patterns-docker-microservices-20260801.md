# Ansible Production-Ready Deployment Patterns for Docker-Based Microservices Infrastructure

## A Comprehensive Guide for IacGenie (11-Service Docker Compose Stack)

**Generated:** 2026-08-01  
**Target Infrastructure:** Single Ubuntu 24.04 VM (15GB RAM, 465GB disk)  
**Services:** PostgreSQL 15, Redis 7, MinIO, OpenBao 2.6.0, Keycloak 26.0, Gitea, LightSerp, SearXNG, NSQD, PageZen, Cloudflare Tunnel, Nginx

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Ansible Architecture Patterns for Production Deployments](#2-ansible-architecture-patterns-for-production-deployments)
3. [Handling Docker Containers with Ansible](#3-handling-docker-containers-with-ansible)
4. [Idempotent Infrastructure-as-Code Patterns](#4-idempotent-infrastructure-as-code-patterns)
5. [Secret Management with Ansible Vault](#5-secret-management-with-ansible-vault)
6. [Configuration Management Best Practices](#6-configuration-management-best-practices)
7. [Testing Ansible Playbooks](#7-testing-ansible-playbooks)
8. [Zero-Downtime Deployment Patterns](#8-zero-downtime-deployment-patterns)
9. [Backup and Disaster Recovery Patterns](#9-backup-and-disaster-recovery-patterns)
10. [Monitoring and Alerting Integration](#10-monitoring-and-alerting-integration)
11. [Multi-Environment Management](#11-multi-environment-management)
12. [Common Pitfalls and Anti-Patterns](#12-common-pitfalls-and-anti-patterns)
13. [Reference: Complete Project Structure for IacGenie](#13-reference-complete-project-structure-for-iacgenie)
14. [Appendix: Playbook Snippets](#14-appendix-playbook-snippets)

---

## 1. Executive Summary

This report provides a production-ready blueprint for deploying, managing, and operating the IacGenie microservices infrastructure using Ansible. The infrastructure consists of 11 Docker Compose services (PostgreSQL, Redis, MinIO, OpenBao, Keycloak, Gitea, LightSerp, SearXNG, NSQD, PageZen) running alongside system-managed services (Nginx, Cloudflare Tunnel) on a single Ubuntu 24.04 VM.

The core philosophy: **use Ansible for bootstrapping, configuration management, and lifecycle orchestration, and use Docker Compose as the container orchestration layer managed by Ansible**. Ansible writes the `docker-compose.yml`, generates secrets, manages TLS certificates, sets up system dependencies, and triggers container lifecycle events — but does NOT replace Docker Compose as the runtime orchestrator.

Key architectural decisions:
- **Ansible writes `docker-compose.yml` templates** rather than using `docker_container`/`docker_compose` modules directly. This keeps the compose file as the source of truth for container lifecycle while Ansible handles everything around it.
- **Environment-variable-driven composition** where Ansible generates compose files from Jinja2 templates with environment-specific values.
- **OpenBao as the secrets backend**, with Ansible Vault used only for bootstrap secrets (OpenBao root token, initial encryption keys).

---

## 2. Ansible Architecture Patterns for Production Deployments

### 2.1 Inventory Design

For a single-VM deployment, use a **multi-tier inventory** that separates host definitions from role assignments:

```yaml
# inventory/
├── hosts.yml              # Target host definitions
├── groups/
│   ├── all.yml            # Variables for all hosts
│   ├── webservers.yml     # Nginx-specific vars
│   ├── databases.yml      # Database service vars
│   ├── microservices.yml  # Microservice containers
│   └── tunnels.yml        # Tunnel proxy vars
├── dev/
│   ├── hosts.yml          # Dev host overrides
│   └── group_vars/
├── staging/
│   ├── hosts.yml
│   └── group_vars/
└── prod/
    ├── hosts.yml          # Prod host (points to same VM for now)
    └── group_vars/
```

**hosts.yml** (single-VM inventory):

```yaml
all:
  children:
    target_host:
      hosts:
        iacgenie:
          ansible_host: 10.0.0.50        # Your VM IP
          ansible_user: deploy             # Non-root deployment user
          ansible_python_interpreter: /usr/bin/python3
    target_host:
      vars:
        ansible_connection: ssh
```

**Key inventory practices:**
- Use `ansible_user` rather than root for security. Create a dedicated `deploy` user with sudo NOPASSWD for Ansible automation.
- Group hosts by service role (`target_host`) so you can run targeted playbooks (e.g., only rotate PostgreSQL certs).
- Use inventory variables for service-specific configurations (ports, volumes, resource limits).

### 2.2 Role Organization

Organize roles by **service domain**, not by Ansible task type. This makes the role structure intuitive:

```
roles/
├── common/                    # Base OS hardening, packages, users
│   ├── tasks/
│   │   ├── main.yml
│   │   ├── packages.yml      # Common system packages
│   │   ├── firewall.yml      # UFW/nftables rules
│   │   ├── ssh_hardening.yml
│   │   └── docker_prereqs.yml
│   ├── handlers/
│   ├── templates/
│   ├── vars/
│   └── defaults/main.yml      # Safe defaults for all environments
│
├── docker/                    # Docker CE installation & config
│   ├── tasks/
│   │   ├── main.yml
│   │   ├── install.yml
│   │   ├── configure_daemon.yml
│   │   └── systemd_override.yml
│   ├── templates/
│   │   └── docker-daemon.json.j2
│   └── vars/
│
├── postgresql/                # PostgreSQL service
│   ├── tasks/
│   │   ├── main.yml
│   │   ├── init_container.yml
│   │   └── volume_setup.yml
│   ├── templates/
│   │   └── postgres.env.j2
│   └── vars/
│
├── redis/                     # Redis service
├── minio/                     # MinIO object storage
├── openbao/                   # OpenBao secrets management
├── keycloak/                  # Keycloak identity provider
├── gitea/                     # Git repository service
├── lightserp/                 # LightSerp API + WebUI
├── searxng/                   # SearXNG search engine
├── nsqd/                      # NSQD message queue
├── pagezen/                   # PageZen crawler
├── nginx/                     # Nginx reverse proxy (systemd)
├── cloudflare_tunnel/         # Cloudflare Tunnel (systemd)
├── backup/                    # Backup orchestration
└── docker-compose/            # Compose file management
```

**Alternative: Collection-based organization**

For larger deployments, package roles into an Ansible collection:

```
collections/
└── ansible_collections/
    └── iacgenie/
        └── roles/
            ├── common/
            ├── docker/
            ├── postgresql/
            └── ...
```

This allows importing with `iacgenie.docker.install_docker` instead of local role references.

### 2.3 Project Structure

Follow the **Ansible Project Structure** best practice with separation of concerns:

```
iacgenie-deploy/                          # Root project directory
├── ansible.cfg                           # Ansible configuration
├── inventory/                            # Multi-environment inventory
│   ├── hosts.yml
│   ├── groups/
│   │   ├── all.yml
│   │   ├── target_host.yml
│   ├── dev/
│   ├── staging/
│   └── prod/
├── group_vars/                           # Global variable definitions
│   ├── all.yml                           # Variables for ALL environments
│   └── target_host.yml                   # Host-specific overrides
├── host_vars/                            # Per-host variables
│   └── iacgenie.yml
├── roles/                                # Ansible roles
│   ├── common/
│   ├── docker/
│   ├── postgresql/
│   ├── redis/
│   ├── minio/
│   ├── openbao/
│   ├── keycloak/
│   ├── gitea/
│   ├── lightserp/
│   ├── searxng/
│   ├── nsqd/
│   ├── pagezen/
│   ├── nginx/
│   ├── cloudflare_tunnel/
│   ├── docker-compose/
│   ├── backup/
│   └── monitoring/
├── plays/                                # Playbooks (execution entry points)
│   ├── site.yml                          # Full deployment (run all roles)
│   ├── bootstrap.yml                     # First-time host setup
│   ├── services.yml                      # Deploy/restart all services
│   ├── rollback.yml                      # Rollback to previous version
│   ├── backup.yml                        # Trigger backup
│   └── verify.yml                        # Health-check verification
├── vars/                                 # Environment-specific variable files
│   ├── defaults.yml
│   ├── postgresql.yml
│   └── services.yml
├── templates/                            # Jinja2 templates for compose files
│   └── docker-compose.yml.j2
├── vault/                                # Encrypted variable files
│   └── secrets.yml.enc
├── tests/                                # Testing infrastructure
│   ├── testinfra/
│   ├── ansible-lint/
│   └── molecule/
├── scripts/                              # Helper scripts
│   ├── init_vault.sh
│   ├── rotate_secrets.sh
│   └── health_check.sh
├── .ansible-lint                         # Ansible-lint configuration
├── .ansible-vault-password               # Vault password file
└── README.md
```

**Key file: `ansible.cfg`**

```ini
[defaults]
inventory      = inventory/hosts.yml
roles_path     = roles/
vars_files     = vars/defaults.yml
host_key_checking = false
retry_files_enabled = false
stdout_callback = yaml
callbacks_enabled = profile_tasks
loader_timeout = 30

[privilege_escalation]
become = true
become_method = sudo
become_user = root
become_ask_pass = false

[ssh_connection]
pipelining = true
control_path = %(directory)s/%%h-%%p-%%r
```

---

## 3. Handling Docker Containers with Ansible

### 3.1 Philosophy: Template-Based Compose Management

For a Docker Compose-based deployment, the recommended pattern is:

1. **Ansible generates the `docker-compose.yml`** via a Jinja2 template with variable substitution
2. **Ansible writes service-specific `.env` files** with secrets and configuration
3. **Ansible uses the `community.docker.docker_compose_v2` module** to apply the compose configuration

This gives you the best of both worlds: Docker Compose manages container lifecycle, while Ansible manages configuration, secrets, and orchestration.

### 3.2 The Main Compose Template

```jinja2
# roles/docker-compose/templates/docker-compose.yml.j2
version: "3.8"

services:
  # ─── PostgreSQL ───
  postgresql:
    image: postgres:{{ postgresql_version }}
    container_name: iacgenie-postgresql
    restart: unless-stopped
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./backups/postgresql:/backups
    environment:
      POSTGRES_USER: "{{ postgresql_user }}"
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      POSTGRES_DB: "{{ postgresql_database }}"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U {{ postgresql_user }} -d {{ postgresql_database }}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - iacgenie_internal
    deploy:
      resources:
        limits:
          memory: {{ postgresql_memory_limit }}
        reservations:
          memory: {{ postgresql_memory_reservation }}
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  # ─── Redis ───
  redis:
    image: redis:{{ redis_version }}-alpine
    container_name: iacgenie-redis
    restart: unless-stopped
    command: redis-server --requirepass {{ redis_password }} --maxmemory {{ redis_maxmemory }} --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "{{ redis_password }}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - iacgenie_internal
    deploy:
      resources:
        limits:
          memory: {{ redis_memory_limit }}

  # ─── MinIO ───
  minio:
    image: minio/minio:latest
    container_name: iacgenie-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    environment:
      MINIO_ROOT_USER: "{{ minio_root_user }}"
      MINIO_ROOT_PASSWORD_FILE: /run/secrets/minio_password
      MINIO_PROMETHEUS_AUTH_TYPE: "public"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 15s
      timeout: 10s
      retries: 5
    networks:
      - iacgenie_internal
    deploy:
      resources:
        limits:
          memory: {{ minio_memory_limit }}

  # ─── OpenBao ───
  openbao:
    image: openbao/openbao:{{ openbao_version }}
    container_name: iacgenie-openbao
    restart: unless-stopped
    cap_add:
      - IPC_LOCK
    volumes:
      - openbao_data:/openbao/data
      - openbao_logs:/openbao/logs
      - ./tls/certs:/openbao/certs
    environment:
      OPENBAO_ADDR: "https://127.0.0.1:8200"
      OPENBAO_TLS_CERT_FILE: /openbao/certs/tls.crt
      OPENBAO_TLS_KEY_FILE: /openbao/certs/tls.key
      OPENBAO_CLUSTER_ADDR: "https://127.0.0.1:8201"
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "https://127.0.0.1:8200/v1/sys/health"]
      interval: 15s
      timeout: 5s
      retries: 10
      start_period: 30s
    networks:
      - iacgenie_internal
    deploy:
      resources:
        limits:
          memory: {{ openbao_memory_limit }}

  # ─── Keycloak ───
  keycloak:
    image: quay.io/keycloak/keycloak:{{ keycloak_version }}
    container_name: iacgenie-keycloak
    restart: unless-stopped
    command: start --http-enabled=false --db=postgres --db-url=jdbc:postgresql://postgresql:5432/keycloak --db-username=keycloak --db-password-file=/run/secrets/keycloak_password
    volumes:
      - keycloak_data:/opt/keycloak/data
    environment:
      KC_HOSTNAME: "{{ keycloak_domain }}"
      KC_PROXY: "edge"
      KC_HTTP_RELATIVE_PATH: "/auth"
    depends_on:
      postgresql:
        condition: service_healthy
    networks:
      - iacgenie_internal
    deploy:
      resources:
        limits:
          memory: {{ keycloak_memory_limit }}

  # ─── Gitea ───
  gitea:
    image: gitea/gitea:{{ gitea_version }}-rootless
    container_name: iacgenie-gitea
    restart: unless-stopped
    volumes:
      - gitea_data:/var/lib/gitea
    environment:
      GITEA__security__INSTALL_LOCK: "true"
      GITEA__database__DB_TYPE: "sqlite3"
      GITEA__database__PATH: "/var/lib/gitea/gitea.db"
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://127.0.0.1:3000/"]
      interval: 15s
      timeout: 5s
      retries: 5
    networks:
      - iacgenie_internal
    deploy:
      resources:
        limits:
          memory: {{ gitea_memory_limit }}

  # ─── LightSerp API ───
  lightsarp-api:
    image: {{ lightsarp_image }}:{{ lightsarp_version }}
    container_name: iacgenie-lightsarp-api
    restart: unless-stopped
    environment:
      LITSARP_DATABASE_URL: "postgresql://{{ postgresql_user }}:{{ postgresql_password }}@postgresql:5432/{{ lightsarp_db }}"
      LITSARP_REDIS_URL: "redis://:{{ redis_password }}@redis:6379/0"
      LITSARP_SECRET_KEY_FILE: /run/secrets/lightsarp_secret_key
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://127.0.0.1:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    depends_on:
      postgresql:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - iacgenie_internal
    deploy:
      resources:
        limits:
          memory: {{ lightsarp_api_memory_limit }}

  # ─── LightSerp WebUI ───
  lightsarp-web:
    image: {{ lightsarp_image }}:{{ lightsarp_version }}
    container_name: iacgenie-lightsarp-web
    restart: unless-stopped
    environment:
      NEXT_PUBLIC_API_URL: "http://127.0.0.1:8000/api"
    depends_on:
      lightsarp-api:
        condition: service_started
    networks:
      - iacgenie_internal
    deploy:
      resources:
        limits:
          memory: {{ lightsarp_web_memory_limit }}

  # ─── SearXNG ───
  searxng:
    image: searxng/searxng:latest
    container_name: iacgenie-searxng
    restart: unless-stopped
    environment:
      SEARXNG_BASE_URL: "https://searx.{{ domain_name }}/"
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://127.0.0.1:8080/"]
      interval: 15s
      timeout: 5s
      retries: 5
    networks:
      - iacgenie_internal
    deploy:
      resources:
        limits:
          memory: {{ searxng_memory_limit }}

  # ─── NSQD ───
  nsqd:
    image: nsqio/nsq:latest
    container_name: iacgenie-nsqd
    restart: unless-stopped
    command: nsqd --broadcast-address=nsqd --tcp-address=0.0.0.0 --http-address=0.0.0.0
    volumes:
      - nsqd_data:/nsqd
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://127.0.0.1:4150/"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - iacgenie_internal
    deploy:
      resources:
        limits:
          memory: {{ nsqd_memory_limit }}

  # ─── PageZen ───
  pagezen:
    image: {{ pagezen_image }}:{{ pagezen_version }}
    container_name: iacgenie-pagezen
    restart: unless-stopped
    environment:
      PG_HOST: "postgresql"
      PG_PORT: "5432"
      PG_USER: "{{ postgresql_user }}"
      PG_PASSWORD_FILE: /run/secrets/pagezen_pg_password
      REDIS_URL: "redis://:{{ redis_password }}@redis:6379/1"
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://127.0.0.1:8090/health"]
      interval: 15s
      timeout: 5s
      retries: 5
    depends_on:
      postgresql:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - iacgenie_internal
    deploy:
      resources:
        limits:
          memory: {{ pagezen_memory_limit }}

networks:
  iacgenie_internal:
    driver: bridge
    ipam:
      config:
        - subnet: "{{ docker_network_subnet }}"
    internal: true

volumes:
  pg_data:
  redis_data:
  minio_data:
  openbao_data:
  openbao_logs:
  keycloak_data:
  gitea_data:
  nsqd_data:
```

### 3.3 Ansible Play for Docker Compose Management

```yaml
# roles/docker-compose/tasks/main.yml
---
- name: "Create project directories"
  ansible.builtin.file:
    path: "{{ iacgenie_project_dir }}/{{ item }}"
    state: directory
    mode: "0755"
  loop:
    - certs
    - certs/tls
    - env
    - env/secrets
    - backups/postgresql
    - backups/minio
    - backups/openbao
  when: iacgenie_project_dir is defined

- name: "Render docker-compose.yml from template"
  ansible.builtin.template:
    src: docker-compose.yml.j2
    dest: "{{ iacgenie_project_dir }}/docker-compose.yml"
    mode: "0644"
  register: compose_file_changed

- name: "Render service-specific .env files"
  ansible.builtin.template:
    src: "{{ item.env_template }}"
    dest: "{{ iacgenie_project_dir }}/{{ item.env_file }}"
    mode: "0600"
  loop:
    - { env_template: 'postgresql.env.j2', env_file: 'env/postgresql.env' }
    - { env_template: 'minio.env.j2', env_file: 'env/minio.env' }
    - { env_template: 'keycloak.env.j2', env_file: 'env/keycloak.env' }
    - { env_template: 'lightsarp.env.j2', env_file: 'env/lightsarp.env' }
    - { env_template: 'pagezen.env.j2', env_file: 'env/pagezen.env' }
  notify: Restart affected services

- name: "Deploy TLS certificates"
  ansible.builtin.copy:
    content: "{{ tls_certificate_content }}"
    dest: "{{ iacgenie_project_dir }}/certs/tls/tls.crt"
    mode: "0644"
  when: tls_certificate_content is defined
  notify: Restart nginx

- name: "Deploy TLS key"
  ansible.builtin.copy:
    content: "{{ tls_private_key_content }}"
    dest: "{{ iacgenie_project_dir }}/certs/tls/tls.key"
    mode: "0600"
  when: tls_private_key_content is defined
  notify: Restart nginx

- name: "Pull latest Docker images"
  community.docker.docker_compose_v2:
    project_src: "{{ iacgenie_project_dir }}"
    files: docker-compose.yml
    pull: always
    state: present
  register: docker_pull_result

- name: "Bring up services"
  community.docker.docker_compose_v2:
    project_src: "{{ iacgenie_project_dir }}"
    files: docker-compose.yml
    state: present
    restarted: "{{ compose_file_changed.changed or docker_pull_result.changed }}"
    wait: true
    timeout: 300
  register: compose_deploy_result
```

### 3.4 Module Selection Guidance

| Task | Module | Why |
|------|--------|-----|
| Install Docker CE | `ansible.builtin.apt` + repo setup | Official Docker repo ensures latest stable |
| Run Docker Compose | `community.docker.docker_compose_v2` | Modern module, YAML compose files, supports v2 CLI |
| Pull images | `community.docker.docker_compose_v2` with `pull: always` | Ensures latest images |
| Stop/Restart service | `community.docker.docker_compose_v2` with `state` changes | Idempotent lifecycle management |
| Monitor containers | `community.docker.docker_container_info` | Query container status, health |
| Cleanup unused images | `community.docker.docker_prune` | Keep disk usage low |
| Docker volume management | `community.docker.docker_volume` | Create/inspect volumes outside compose |

**Why NOT `docker_container` for each service?**  
The `docker_container` module manages individual containers without compose. For 11+ services, this creates:
- Massive playbooks with 11x container definitions
- Complex dependency management (depends_on becomes manual ordering)
- Network/volume management duplication
- No automatic scaling or restart policies

The template+compose approach is cleaner and more maintainable.

---

## 4. Idempotent Infrastructure-as-Code Patterns

### 4.1 Core Idempotency Principles

Idempotency means running the same playbook multiple times produces the same final state. Every Ansible task must be idempotent.

**Key patterns:**

1. **Use `state` parameter appropriately** — every resource module has a `state` parameter (`present`, `absent`, `started`, `stopped`, `restarted`).

2. **Use `register` + `when` for conditional actions:**

```yaml
- name: "Check if PostgreSQL volume exists"
  community.docker.docker_volume:
    name: iacgenie_pg_data
    state: present
  register: pg_volume

- name: "Initialize PostgreSQL data only on first run"
  ansible.builtin.command:
    cmd: echo "PostgreSQL data directory initialized"
  when: pg_volume is changed  # Only runs on first creation
```

3. **Use `become` consistently** for privilege escalation:

```yaml
- name: "Ensure Docker service is enabled"
  ansible.builtin.service:
    name: docker
    state: started
    enabled: true
  become: true
```

### 4.2 Docker-Specific Idempotency

Docker containers have built-in idempotency through `restart: unless-stopped`. Your Ansible role must complement this:

```yaml
# roles/docker/tasks/configure_docker.yml
---
- name: "Configure Docker daemon with resource limits"
  ansible.builtin.template:
    src: docker-daemon.json.j2
    dest: /etc/docker/daemon.json
    mode: "0644"
    owner: root
    group: root
  notify: Restart Docker service

- name: "Add deploy user to docker group"
  ansible.builtin.user:
    name: deploy
    groups: docker
    append: true
    shell: /bin/bash
  become: true

- name: "Ensure no duplicate network definitions"
  community.docker.docker_network:
    name: iacgenie_internal
    driver: bridge
    ipam_driver: default
    ipam_config:
      - subnet: "{{ docker_network_subnet }}"
    state: present
    internal: true
  become: true
```

**Docker resource idempotency table:**

| Resource | Module | Idempotency Mechanism |
|----------|--------|----------------------|
| Container | `docker_compose_v2` | Reconciles with compose file |
| Network | `docker_network` | Creates if missing, reconfigures only if needed |
| Volume | `docker_volume` | Creates if missing, skips if exists |
| Image | `docker_image` | Pulls only if tag differs or `force: true` |
| Container restart | `docker_compose_v2` with `restarted: true` | Graceful stop + start |

### 4.3 Using `check_mode` and `diff`

Enable these in CI to catch non-idempotent tasks before deployment:

```yaml
# ansible.cfg
[defaults]
check_mode = false         # Set true in CI
diff = true                 # Show what would change
```

Test idempotency in CI:
```bash
# First run: deploy
ansible-playbook plays/site.yml -i inventory/prod/hosts.yml --vault-password-file .ansible-vault-password

# Second run: verify idempotency (no changes expected)
ansible-playbook plays/site.yml -i inventory/prod/hosts.yml --vault-password-file .ansible-vault-password --check --diff
```

The second run should report `changed=0` for all tasks.

### 4.4 Use `block` and `rescue` for resilient idempotency

```yaml
- name: "Deploy OpenBao configuration"
  block:
    - name: "Extract OpenBao TLS certificate"
      ansible.builtin.template:
        src: openbao-tls.j2
        dest: "{{ openbao_tls_dir }}/tls.crt"
        mode: "0644"

    - name: "Apply OpenBao systemd service"
      ansible.builtin.copy:
        src: openbao.service
        dest: /etc/systemd/system/openbao.service
        mode: "0644"

  rescue:
    - name: "Restore previous configuration on failure"
      ansible.builtin.debug:
        msg: "OpenBao deployment failed. Manual intervention may be required."

    - name: "Attempt rollback"
      ansible.builtin.shell: |
        systemctl daemon-reload
        systemctl restart openbao
      ignore_errors: true
```

### 4.5 Template Idempotency with `diff` on Templates

When using Jinja2 templates, avoid unnecessary file changes:

```yaml
- name: "Render docker-compose.yml (idempotent)"
  ansible.builtin.template:
    src: docker-compose.yml.j2
    dest: "{{ iacgenie_project_dir }}/docker-compose.yml"
    mode: "0644"
    # Use 'check_mode' safe templates (no random variables)
  register: compose_result
  # Always triggers on template change — add content comparison if needed

# For files that change frequently (timestamps, PIDs), use 'content' with
# 'ansible.builtin.copy' and a 'checksum' check
- name: "Ensure .env file content matches expected"
  ansible.builtin.copy:
    content: "{{ lookup('template', 'postgresql.env.j2') }}"
    dest: "{{ iacgenie_project_dir }}/env/postgresql.env"
    mode: "0600"
  register: env_file
  # Ansible compares file content, not just modification time
```

---

## 5. Secret Management with Ansible Vault

### 5.1 Two-Layer Secret Strategy

For your infrastructure, use a **two-layer approach**:

1. **Ansible Vault** — encrypts bootstrap secrets and Ansible-level credentials (OpenBao root token, Docker registry passwords)
2. **OpenBao KV** — runtime secrets for services (database passwords, API keys, application secrets)

```
secret_layer_1 = Ansible Vault          # Infrastructure bootstrap
secret_layer_2 = OpenBao KV Store       # Runtime application secrets

Flow:
1. Ansible Vault decrypts the OpenBao root token
2. OpenBao root token initializes OpenBao KV engine
3. Ansible writes service secrets into OpenBao KV
4. Docker containers read secrets from OpenBao at startup
5. Ansible Vault is no longer needed for runtime secrets
```

### 5.2 Ansible Vault Setup

**Encrypted variable files:**

```yaml
# vault/secrets.yml.enc  (encrypted with ansible-vault)
---
# PostgreSQL secrets
postgresql_user: iacgenie
postgresql_password: "{{ vault_pg_password }}"      # Get from OpenBao at runtime
postgresql_database: iacgenie

# MinIO secrets
minio_root_user: iacgenie
minio_root_password: "{{ vault_minio_password }}"

# Keycloak
keycloak_admin_password: "{{ vault_keycloak_admin_pw }}"

# LightSerp
lightsarp_secret_key: "{{ vault_lightsarp_secret }}"

# OpenBao (bootstrap)
openbao_root_token: "{{ vault_openbao_root_token }}"
openbao_init_key: "{{ vault_openbao_init_key }}"

# TLS
tls_private_key: "{{ vault_tls_key }}"
tls_certificate: "{{ vault_tls_cert }}"

# Domain configuration
domain_name: iacgenie.example.com
```

**Initialize Vault:**

```bash
# Create vault password file (gitignored)
echo "your-strong-vault-password" > ~/.ansible-vault-password
chmod 600 ~/.ansible-vault-password

# Encrypt a new variable file
ansible-vault create vault/secrets.yml

# Edit encrypted file
ansible-vault edit vault/secrets.yml

# Encrypt existing file
ansible-vault encrypt vault/secrets.yml

# Decrypt (not recommended — you want encryption at rest)
ansible-vault decrypt vault/secrets.yml

# Use with playbook
ansible-playbook plays/site.yml --vault-password-file ~/.ansible-vault-password
```

### 5.3 Vault in Playbooks

```yaml
# plays/site.yml
---
- name: "Include vault secrets"
  ansible.builtin.include_vars:
    file: vault/secrets.yml
  no_log: true  # Prevent secret display in output

- name: "Deploy services with secrets"
  ansible.builtin.include_tasks:
    file: roles/docker-compose/tasks/main.yml
```

**Playbook execution with vault:**

```bash
# Option 1: Password file (recommended for automation)
ansible-playbook plays/site.yml --vault-password-file ~/.ansible-vault-password

# Option 2: Environment variable
export ANSIBLE_VAULT_PASSWORD_FILE=~/.ansible-vault-password
ansible-playbook plays/site.yml

# Option 3: Prompt
ansible-playbook plays/site.yml --ask-vault-pass
```

### 5.4 OpenBao as Runtime Secrets Backend

Once OpenBao is initialized, migrate runtime secrets there:

```yaml
# roles/openbao/tasks/write_secrets.yml
---
- name: "Enable KV version 2 secrets engine"
  community.general.hashi_vault:
    url: "{{ openbao_addr }}"
    token: "{{ openbao_root_token }}"
    validate_certs: false
    engine_path: secret
    type: kv
    state: present
    silent: true
    ca_cert: "{{ openbao_tls_dir }}/tls.crt"
  no_log: true

- name: "Write PostgreSQL credentials to OpenBao"
  community.general.hashi_vault:
    url: "{{ openbao_addr }}"
    token: "{{ openbao_root_token }}"
    validate_certs: false
    engine_path: secret
    data:
      username: "{{ postgresql_user }}"
      password: "{{ postgresql_password }}"
      host: "postgresql"
      port: "5432"
      database: "{{ postgresql_database }}"
    state: present
  no_log: true
  notify: Restart PostgreSQL
```

Docker containers read from OpenBao at startup via init containers or startup scripts:

```yaml
# In the docker-compose template, for services needing OpenBao secrets:
  postgresql:
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets:
      - postgres_password

secrets:
  postgres_password:
    external: true  # Mounted by orchestration layer
```

### 5.5 Key Management

**Vault password management:**

```
Security practices:
├── Store vault password in a hardware security module or
│   a dedicated secrets manager (OpenBao itself!)
├── Use different vault passwords for dev/staging/prod
├── Never store vault password in git
├── Use SSH-agent for Ansible vault operations in CI
└── Rotate vault password quarterly
```

**Key rotation playbook:**

```yaml
# plays/rotate_secrets.yml
---
- name: "Rotate database passwords"
  hosts: target_host
  tasks:
    - name: "Generate new PostgreSQL password"
      ansible.builtin.set_fact:
        new_pg_password: "{{ lookup('password', '/dev/null length=32 chars=ascii_letters,digits') }}"

    - name: "Update password in OpenBao"
      community.general.hashi_vault:
        url: "{{ openbao_addr }}"
        token: "{{ openbao_root_token }}"
        engine_path: secret/postgresql
        data:
          password: "{{ new_pg_password }}"
        state: present

    - name: "Update PostgreSQL container password"
      ansible.builtin.template:
        src: docker-compose.yml.j2
        dest: "{{ iacgenie_project_dir }}/docker-compose.yml"

    - name: "Rolling restart of PostgreSQL"
      community.docker.docker_compose_v2:
        project_src: "{{ iacgenie_project_dir }}"
        files: docker-compose.yml
        restarted: true
```

---

## 6. Configuration Management Best Practices

### 6.1 Variable Precedence

Ansible evaluates variables in a specific order. Understanding this is critical:

```
Lowest priority → Highest priority:
1. role/defaults/main.yml (role defaults — safe fallbacks)
2. inventory/group_vars/all.yml (global group variables)
3. inventory/group_vars/target_host.yml (host group variables)
4. inventory/host_vars/iacgenie.yml (specific host)
5. role/vars/main.yml (role variables — overrides defaults)
6. playbook vars (vars: in the play)
7. command-line -e overrides (highest priority)
8. fact cache (from setup module)
```

**Best practice:** Always define sensible defaults in `role/defaults/main.yml`:

```yaml
# roles/postgresql/defaults/main.yml
---
postgresql_version: "15"
postgresql_user: "iacgenie"
postgresql_database: "iacgenie"
postgresql_memory_limit: "4g"
postgresql_memory_reservation: "1g"
postgresql_data_dir: "/var/lib/postgresql/data"
postgresql_max_connections: 200
postgresql_shared_buffers: "256MB"
postgresql_enforces_password_encryption: true
```

### 6.2 Template-Driven Configuration

Use Jinja2 templates for all configuration that varies by environment:

```jinja2
# roles/nginx/templates/nginx.conf.j2
# /etc/nginx/nginx.conf — generated by Ansible

user www-data;
worker_processes auto;
pid /run/nginx.pid;
error_log /var/log/nginx/error.log warn;

events {
    worker_connections {{ nginx_worker_connections | default(1024) }};
    multi_accept on;
}

http {
    # Compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level {{ nginx_gzip_level | default(6) }};
    gzip_types text/plain text/css application/json application/javascript text/xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

    # Timeouts
    proxy_connect_timeout 10s;
    proxy_read_timeout 60s;
    proxy_send_timeout 60s;

    # Upstream definitions
{% for service in nginx_upstreams %}
    upstream {{ service.name }} {
        server {{ service.address }}:{{ service.port }};
        keepalive {{ service.keepalive | default(32) }};
    }
{% endfor %}

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name {{ domain_name }};

        ssl_certificate     {{ tls_cert_path }};
        ssl_certificate_key {{ tls_key_path }};
        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;
        ssl_session_cache   shared:SSL:10m;
        ssl_session_timeout 1d;
        ssl_session_tickets off;

{% for location in nginx_locations %}
        location {{ location.path }} {
{% if location.proxy_pass %}
            proxy_pass {{ location.proxy_pass }};
{% endif %}
{% if location.rate_limit %}
            limit_req zone={{ location.rate_limit.zone }} burst={{ location.rate_limit.burst }} nodelay;
{% endif %}
{% if location.extra_config %}
{{ location.extra_config | indent(12) }}
{% endif %}
        }
{% endfor %}

        # Health check endpoint
        location /health {
            access_log off;
            return 200 "ok\n";
            add_header Content-Type text/plain;
        }
    }
}
```

### 6.3 Role Variable Organization

```
roles/nginx/
├── defaults/main.yml      # Safe defaults (worker_processes, timeouts)
├── vars/main.yml          # Required vars (no fallbacks)
├── tasks/
│   ├── main.yml           # Entry point
│   ├── install.yml        # Package installation
│   ├── configure.yml      # Configuration file management
│   ├── certs.yml          # TLS certificate handling
│   ├── sites.yml          # Site configuration
│   └── service.yml        # Service management
├── handlers/main.yml      # Reload nginx
├── templates/
│   ├── nginx.conf.j2      # Main config template
│   ├── nginx-upstream.conf.j2  # Upstream definitions
│   └── sites-available/
│       └── iacgenie.conf.j2
└── files/                 # Static files (robots.txt, etc.)
```

### 6.4 Dynamic Discovery with Facts

Use Ansible facts to adapt configurations dynamically:

```yaml
- name: "Gather system facts"
  ansible.builtin.setup:
    filter:
      - ansible_memtotal_mb
      - ansible_processor_vcpus
      - ansible_os_family
      - ansible_distribution_version

- name: "Set resource limits based on available memory"
  ansible.builtin.set_fact:
    postgresql_memory_limit: "{{ (ansible_memtotal_mb * 0.25) | round(0, 'ceil') | int }}MB"
    redis_memory_limit: "{{ (ansible_memtotal_mb * 0.15) | round(0, 'ceil') | int }}MB"
    docker_daemon_storage_max_size: "{{ (ansible_memtotal_mb * 0.6) | round(0, 'ceil') | int }}G"
  when:
    - ansible_memtotal_mb is defined
```

### 6.5 Using `include_vars` Strategically

```yaml
# Site playbook with layered variable loading
---
- name: "Load base configuration"
  hosts: target_host
  become: true

  pre_tasks:
    - name: "Load environment-specific variables"
      ansible.builtin.include_vars:
        file: "{{ environment }}/{{ inventory_hostname }}.yml"

    - name: "Load global service variables"
      ansible.builtin.include_vars:
        dir: group_vars
        extensions:
          - yml
          - yaml
      tags: config

  roles:
    - role: common
    - role: docker
    - role: postgresql
    - role: redis
    - role: minio
    - role: openbao
    - role: keycloak
    - role: gitea
    - role: lightserp
    - role: searxng
    - role: nsqd
    - role: pagezen
    - role: nginx
    - role: cloudflare_tunnel
    - role: docker-compose
    - role: backup
    - role: monitoring
```

---

## 7. Testing Ansible Playbooks

### 7.1 Testing Pyramid for Ansible

```
            ┌─────────────┐
            │  E2E Tests  │  ← Deploy to staging VM, run smoke tests
            ├─────────────┤
          ┌─┤ Integration  │  ← Molecule tests per role
          │ └─────────────┘
        ┌─┤ Linter Tests │  ← ansible-lint (CI gate)
        │ └─────────────┘
      ┌─┤ Unit Tests     │  ← Test variable resolution, template rendering
      └─┴─────────────┘
```

### 7.2 Ansible-Lint (CI Gate)

**Install:**
```bash
pipx install ansible-lint
# Or via uv
uv tool install ansible-lint
```

**Configuration:**
```yaml
# .ansible-lint
---
profile: production
skip_list:
  - no-changed-when           # Some docker tasks don't report changes
  - command-instead-of-shell  # Acceptable for system commands
  - yaml[line-length]         # Enforce your own line length
  - no-handler                # Acceptable when handlers aren't needed
warn_list:
  - experimental           # Lint experimental rules as warnings
  - role-name             # Be lenient on role naming in early dev
exclude_paths:
  - vendor/
  - .git/
  - tests/
```

**Run in CI:**
```bash
ansible-lint -v plays/ roles/
```

**GitHub Actions integration:**
```yaml
# .github/workflows/ansible-lint.yml
name: Ansible Lint
on: [pull_request, push]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: redhat-action-run-at-ansible-lint@v1
```

### 7.3 Molecule Testing

Molecule provides integration testing for Ansible roles. Set up per-role:

```bash
# Install molecule
pipx install molecule molecule-plugins[docker] ansible-lint

# Initialize a role with molecule
molecule init role postgresql -d docker

# Generated structure:
# molecule/postgresql/
# ├── molecule.yml          # Test configuration
# ├── platform.yml          # Docker container definitions
# ├── converge.yml          # Test playbook
# ├── verify.yml            # Post-deployment verification
# └── tests/
#     └── test_molecule.py  # Testinfra tests
```

**Example Molecule test for PostgreSQL:**

```yaml
# molecule/postgresql/molecule.yml
---
driver:
  name: docker
platforms:
  - name: iacgenie-postgres-test
    image: ubuntu:24.04
    privileged: true
    pre_build_image: true
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup:rw
    groups:
      - target_host
provisioner:
  name: ansible
  playbooks:
    converge: ../roles/common/tasks/main.yml
    verify: ./verify.yml
verifier:
  name: ansible
  extra_args:
    - --lint
```

```python
# molecule/postgresql/tests/test_molecule.py
import testinfra.utils.ansible_runner

def test_docker_is_installed(host):
    docker = host.package("docker.io")
    assert docker.is_installed

def test_postgresql_volume_exists(host):
    docker = host.docker()
    containers = docker.containers(filters={"name": "iacgenie-postgresql"})
    assert len(containers) > 0

def test_postgresql_healthcheck(host):
    """Verify PostgreSQL responds to connections"""
    pg_container = host.docker().containers(
        filters={"name": "iacgenie-postgresql"},
        all=True
    )[0]
    assert pg_container["State"]["Running"]
    # Check health status
    health = pg_container.get("Health", {})
    assert health.get("Status") in ["healthy", "starting"]
```

### 7.4 Testinfra for System-Level Testing

```python
# tests/testinfra/test_services.py
import testinfra.utils.ansible_runner

def test_postgresql_container(host):
    """Test that PostgreSQL container is running and healthy"""
    docker = host.docker()
    containers = docker.containers(filters={"name": "iacgenie-postgresql"})
    assert len(containers) == 1

    container = containers[0]
    assert container["State"] == "running"

def test_redis_container(host):
    docker = host.docker()
    containers = docker.containers(filters={"name": "iacgenie-redis"})
    assert len(containers) == 1
    assert containers[0]["State"] == "running"

def test_nginx_systemd_service(host):
    """Test Nginx is running as a systemd service"""
    nginx = host.service("nginx")
    assert nginx.is_running
    assert nginx.is_enabled

def test_docker_network_exists(host):
    """Test that the internal Docker network exists"""
    result = host.command("docker network inspect iacgenie_internal")
    assert result.rc == 0

def test_docker_network_isolate(host):
    """Test internal network isolation"""
    net = host.docker().networks(filters={"name": "iacgenie_internal"})[0]
    assert net["Internal"] is True

def test_firewall_rules(host):
    """Test UFW rules allow required ports"""
    ufw = host.command("ufw status verbose")
    assert "Status: active" in ufw.stdout
    assert "22/tcp" in ufw.stdout
    assert "80/tcp" in ufw.stdout
    assert "443/tcp" in ufw.stdout
    # Internal ports should NOT be exposed
    assert "8080/tcp" not in ufw.stdout  # SearXNG internal
```

### 7.5 CI Pipeline Pattern

```yaml
# .github/workflows/ansible-ci.yml (if using GitHub-hosted runner + VM)
name: Ansible CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install ansible-lint ansible-core
      - run: ansible-lint -v .

  test-molecule:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install molecule molecule-plugins[docker] ansible-core
      - run: molecule test -d docker --destroy=never

  validate-inventory:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ansible-core
      - run: ansible-inventory --list -i inventory/
      - run: ansible-playbook plays/site.yml --check --diff --limit target_host

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ansible-lint
      - run: ansible-lint --profile=production .
```

---

## 8. Zero-Downtime Deployment Patterns

### 8.1 Rolling Service Updates

For single-instance services, true rolling updates are challenging. Use **dependency-aware restart sequencing**:

```yaml
# plays/services.yml — Ordered service update
---
- name: "Update all services"
  hosts: target_host
  become: true

  tasks:
    - name: "Step 1: Update supporting services (no traffic impact)"
      community.docker.docker_compose_v2:
        project_src: "{{ iacgenie_project_dir }}"
        files: docker-compose.yml
        services:
          - postgresql
          - redis
          - nsqd
        pull: always
        state: present

    - name: "Step 2: Pull new images for application services"
      community.docker.docker_compose_v2:
        project_src: "{{ iacgenie_project_dir }}"
        files: docker-compose.yml
        services:
          - lightsarp-api
          - lightsarp-web
          - searxng
          - pagezen
        pull: always

    - name: "Step 3: Health check supporting services"
      ansible.builtin.command:
        cmd: docker inspect --format='{{ "{{" }}.State.Health.Status{{ "}}" }}' iacgenie-{{ item }}
      loop:
        - postgresql
        - redis
        - nsqd
      register: health_checks

    - name: "Fail if supporting services are unhealthy"
      ansible.builtin.fail:
        msg: "Supporting service {{ item.item }} is not healthy"
      when: item.stdout != "healthy"
      loop: "{{ health_checks.results }}"

    - name: "Step 4: Restart application services in dependency order"
      community.docker.docker_compose_v2:
        project_src: "{{ iacgenie_project_dir }}"
        files: docker-compose.yml
        services:
          - keycloak        # Depends on postgresql
          - gitea
          - lightsarp-api   # Depends on postgresql, redis
          - lightsarp-web   # Depends on lightsarp-api
          - searxng
          - pagezen         # Depends on postgresql, redis

    - name: "Step 5: Verify all services are healthy"
      ansible.builtin.command:
        cmd: docker inspect --format='{{ "{{" }}.State.Health.Status{{ "}}" }}' iacgenie-{{ item }}
      loop:
        - postgresql
        - redis
        - minio
        - openbao
        - keycloak
        - gitea
        - lightsarp-api
        - searxng
        - nsqd
        - pagezen
      register: final_health
      failed_when: false

    - name: "Report health check results"
      ansible.builtin.debug:
        msg: "Service {{ item.item }}: {{ item.stdout }}"
      loop: "{{ final_health.results }}"
```

### 8.2 Blue-Green Deployment for Nginx

Nginx is the only entry point — implement blue-green at the reverse-proxy level:

```yaml
# roles/nginx/tasks/blue_green.yml
---
- name: "Stage new Nginx configuration"
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf.new
    mode: "0644"

- name: "Test new Nginx configuration"
  ansible.builtin.command:
    cmd: nginx -t -c /etc/nginx/nginx.conf.new
  register: nginx_test
  changed_when: false

- name: "Swap configuration atomically"
  ansible.builtin.shell: |
    mv /etc/nginx/nginx.conf.new /etc/nginx/nginx.conf
  when: nginx_test.rc == 0

- name: "Graceful reload Nginx"
  ansible.builtin.command:
    cmd: nginx -s reload
  when: nginx_test.rc == 0
  # Zero-downtime: nginx reloads worker processes without dropping connections
```

### 8.3 Health-Check Based Deployment

```yaml
# plays/verify.yml — Post-deployment verification
---
- name: "Verify service health after deployment"
  hosts: target_host
  become: true

  tasks:
    - name: "Check service health endpoints"
      ansible.builtin.uri:
        url: "http://127.0.0.1:{{ item.port }}/health"
        method: GET
        status_code: 200
        timeout: 10
        register: health_response
      loop:
        - { name: postgresql, port: 5432 }
        - { name: redis, port: 6379 }
        - { name: lightSerp API, port: 8000 }
        - { name: SearXNG, port: 8080 }
        - { name: PageZen, port: 8090 }
        - { name: Gitea, port: 3000 }
      register: service_health

    - name: "Check Nginx reverse proxy"
      ansible.builtin.uri:
        url: "https://{{ domain_name }}/health"
        method: GET
        status_code: 200
        validate_certs: false
      register: nginx_health

    - name: "Check Cloudflare Tunnel connectivity"
      ansible.builtin.command:
        cmd: cloudflared tunnel status
      register: tunnel_status

    - name: "Report deployment verification results"
      ansible.builtin.debug:
        msg: "Service {{ item.item.name }}: {{ item.stdout }}"
      loop: "{{ service_health.results }}"

    - name: "Fail if any service is unhealthy"
      ansible.builtin.fail:
        msg: "Service health check failed"
      when: >
        item.stdout is defined and
        ('"code":200' not in item.stdout)
      loop: "{{ service_health.results }}"
```

### 8.4 Backup-Before-Update Pattern

Always backup before updates:

```yaml
# plays/services.yml — Pre-update backup
---
- name: "Pre-update backup"
  hosts: target_host
  become: true

  pre_tasks:
    - name: "Create backup timestamp"
      ansible.builtin.set_fact:
        backup_timestamp: "{{ ansible_date_time.iso8601_basic_short }}"

    - name: "Backup PostgreSQL"
      ansible.builtin.command:
        cmd: >
          docker exec iacgenie-postgresql
          pg_dump -U {{ postgresql_user }} -d {{ postgresql_database }}
          | gzip > {{ iacgenie_project_dir }}/backups/postgresql/pre-update-{{ backup_timestamp }}.sql.gz
      register: pg_backup

    - name: "Backup MinIO"
      ansible.builtin.command:
        cmd: >
          docker run --rm --network host
          minio/mc mirror
          /data minio-bucket-backup/pre-update-{{ backup_timestamp }}
      register: minio_backup
      ignore_errors: true

  post_tasks:
    - name: "Verify backup exists"
      ansible.builtin.stat:
        path: "{{ item }}"
      loop:
        - "{{ iacgenie_project_dir }}/backups/postgresql/pre-update-{{ backup_timestamp }}.sql.gz"
      register: backup_files

    - name: "Abort if backup failed"
      ansible.builtin.fail:
        msg: "Backup verification failed"
      when: not backup_files.results[0].stat.exists
```

---

## 9. Backup and Disaster Recovery Patterns

### 9.1 Backup Strategy Overview

```
Backup Layers:
┌─────────────────────────────────────────────────┐
│ Layer 1: Database snapshots (PostgreSQL)        │ ← Critical
│ Layer 2: MinIO versioning                       │ ← Critical
│ Layer 3: OpenBao raft snapshots                 │ ← Critical
│ Layer 4: Docker volumes (Gitea, etc.)           │ ← Important
│ Layer 5: Configuration files (git-tracked)      ← Infrastructure
│ Layer 6: TLS certificates (re-download from CF) │ ← Disposable
└─────────────────────────────────────────────────┘
```

### 9.2 Automated Backup Playbook

```yaml
# plays/backup.yml
---
- name: "Execute full infrastructure backup"
  hosts: target_host
  become: true

  vars:
    backup_base_dir: "{{ iacgenie_project_dir }}/backups"
    backup_timestamp: "{{ ansible_date_time.iso8601_basic }}"
    backup_dir: "{{ backup_base_dir }}/full-{{ backup_timestamp }}"

  tasks:
    # ─── PostgreSQL Backup ───
    - name: "Create PostgreSQL logical backup"
      ansible.builtin.command:
        cmd: >
          docker exec iacgenie-postgresql
          pg_dumpall -U {{ postgresql_user }}
          | gzip > {{ backup_dir }}/postgresql/{{ backup_timestamp }}.sql.gz
      environment:
        PGPASSWORD: "{{ postgresql_password }}"
      register: pg_backup_result

    - name: "Verify PostgreSQL backup"
      ansible.builtin.command:
        cmd: "gzip -t {{ backup_dir }}/postgresql/{{ backup_timestamp }}.sql.gz && echo OK"
      register: pg_backup_verify
      failed_when: pg_backup_verify.stdout.strip() != "OK"

    # ─── MinIO Backup ───
    - name: "Create MinIO snapshot via mc snapshot"
      ansible.builtin.command:
        cmd: >
          docker run --rm --network host
          minio/mc snapshot create
          {{ iacgenie_minio_alias }}/{{ item.bucket }}
      loop: "{{ minio_buckets }}"
      register: minio_backup_result

    # ─── OpenBao Snapshot ───
    - name: "Create OpenBao raft snapshot"
      ansible.builtin.command:
        cmd: >
          docker exec iacgenie-openbao
          openbao operator raft snapshot
          take {{ backup_dir }}/openbao/raft-{{ backup_timestamp }}.snapshot
      register: openbao_backup_result

    # ─── Gitea Backup ───
    - name: "Backup Gitea data"
      ansible.builtin.command:
        cmd: >
          tar czf {{ backup_dir }}/gitea/gitea-{{ backup_timestamp }}.tar.gz
          -C /var/lib/docker/volumes/iacgenie_gitea_data/_data .
      register: gitea_backup_result

    # ─── Encrypt and Compress Backup ───
    - name: "Encrypt backup with GPG"
      ansible.builtin.command:
        cmd: "gpg --batch --yes --trust-model always -e -r {{ backup_recipient_key }} -o {{ backup_dir }}/encrypted {{ backup_dir }}"
      register: encrypt_result

    # ─── Upload to Offsite Storage ───
    - name: "Upload encrypted backup to MinIO"
      ansible.builtin.command:
        cmd: >
          docker run --rm --network host
          minio/mc cp --recursive
          {{ backup_dir }}/encrypted
          {{ iacgenie_minio_alias }}/backups/full-{{ backup_timestamp }}
      register: upload_result

    # ─── Cleanup Local Backups ───
    - name: "Remove unencrypted backup data"
      ansible.builtin.file:
        path: "{{ backup_dir }}"
        state: absent
      when: encrypt_result.rc == 0

    # ─── Rotate Old Backups ───
    - name: "Remove backups older than {{ backup_retention_days }} days"
      ansible.builtin.find:
        paths: "{{ backup_base_dir }}"
        patterns: "full-*"
        age: "{{ backup_retention_days }}d"
      register: old_backups

    - name: "Delete old backups"
      ansible.builtin.file:
        path: "{{ item.path }}"
        state: absent
      loop: "{{ old_backups.files }}"
```

### 9.3 Disaster Recovery Runbook

```yaml
# plays/restore.yml
---
- name: "Restore infrastructure from backup"
  hosts: target_host
  become: true

  vars:
    restore_source: "/path/to/backup/full-{{ restore_date }}"

  tasks:
    - name: "Stop all services"
      community.docker.docker_compose_v2:
        project_src: "{{ iacgenie_project_dir }}"
        files: docker-compose.yml
        state: stopped

    - name: "Restore PostgreSQL"
      ansible.builtin.command:
        cmd: >
          gunzip -c {{ restore_source }}/postgresql/*.sql.gz
          | docker exec -i iacgenie-postgresql psql -U {{ postgresql_user }}
      environment:
        PGPASSWORD: "{{ postgresql_password }}"

    - name: "Restore MinIO"
      ansible.builtin.command:
        cmd: >
          docker run --rm --network host
          minio/mc restore create
          {{ iacgenie_minio_alias }}/{{ item.bucket }}
          {{ iacgenie_minio_alias }}/{{ item.bucket }}/snapshots/restore-snapshot
      loop: "{{ minio_buckets }}"

    - name: "Restore OpenBao"
      ansible.builtin.command:
        cmd: >
          docker exec -i iacgenie-openbao
          openbao operator raft snapshot restore
          {{ restore_source }}/openbao/raft-*.snapshot
      register: openbao_restore

    - name: "Restore Gitea"
      ansible.builtin.command:
        cmd: >
          tar xzf {{ restore_source }}/gitea/gitea-*.tar.gz
          -C /var/lib/docker/volumes/iacgenie_gitea_data/_data/

    - name: "Restart services"
      community.docker.docker_compose_v2:
        project_src: "{{ iacgenie_project_dir }}"
        files: docker-compose.yml
        state: present
        restarted: true

    - name: "Verify restored services"
      ansible.builtin.command:
        cmd: docker inspect --format='{{ "{{" }}.State.Health.Status{{ "}}" }}' iacgenie-{{ item }}
      loop:
        - postgresql
        - redis
        - minio
        - openbao
      register: restore_health

    - name: "Report restore verification"
      ansible.builtin.debug:
        msg: "Service {{ item.item }}: {{ item.stdout }}"
      loop: "{{ restore_health.results }}"
```

### 9.4 Backup Schedule

**Cron-based automation (Ansible cron module):**

```yaml
# roles/backup/tasks/cron_schedule.yml
---
- name: "Schedule daily PostgreSQL backup"
  ansible.builtin.cron:
    name: "iacgenie-postgresql-daily-backup"
    job: >
      docker exec iacgenie-postgresql
      pg_dump -U {{ postgresql_user }} -d {{ postgresql_database }}
      | gzip > {{ iacgenie_project_dir }}/backups/postgresql/daily-$(date +%Y%m%d).sql.gz
    minute: "0"
    hour: "2"
    user: deploy

- name: "Schedule daily full backup with offsite upload"
  ansible.builtin.cron:
    name: "iacgenie-full-backup-daily"
    job: "{{ iacgenie_project_dir }}/scripts/backup.sh"
    minute: "30"
    hour: "3"
    user: deploy

- name: "Schedule weekly Offsite sync"
  ansible.builtin.cron:
    name: "iacgenie-backup-sync-weekly"
    job: "aws s3 sync {{ backup_base_dir }}/offsite/ s3://iacgenie-backups/"
    day: "1"
    hour: "4"
    minute: "0"
    user: deploy
```

---

## 10. Monitoring and Alerting Integration

### 10.1 Container-Level Health Monitoring

Docker health checks provide basic monitoring. For comprehensive observability:

```yaml
# In docker-compose.yml.j2 — add Prometheus metrics to key services
  postgresql:
    image: postgres:{{ postgresql_version }}
    # Use postgres_exporter sidecar
    # ...

  minio:
    environment:
      MINIO_PROMETHEUS_AUTH_TYPE: "public"
    # Built-in Prometheus metrics at :9000/metrics/minio/

  redis:
    # Use redis_exporter sidecar or dedicated metrics container
    # ...
```

### 10.2 Node Exporter for System Monitoring

```yaml
# Add to docker-compose.yml.j2
  node-exporter:
    image: prom/node-exporter:latest
    container_name: iacgenie-node-exporter
    restart: unless-stopped
    network_mode: host
    pid: host
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://127.0.0.1:9100/metrics"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 10.3 Monitoring Playbook

```yaml
# roles/monitoring/tasks/main.yml
---
- name: "Deploy Prometheus configuration"
  ansible.builtin.template:
    src: prometheus.yml.j2
    dest: /opt/monitoring/prometheus/prometheus.yml
    mode: "0644"
  notify: Restart Prometheus

- name: "Deploy Grafana dashboards"
  ansible.builtin.copy:
    src: "{{ item }}"
    dest: /opt/monitoring/grafana/dashboards/{{ item }}
    mode: "0644"
  loop:
    - docker-containers.json
    - postgresql-overview.json
    - redis-overview.json
    - nginx-stats.json
    - system-resources.json

- name: "Configure alerting rules"
  ansible.builtin.template:
    src: alerting_rules.yml.j2
    dest: /opt/monitoring/prometheus/alerting_rules.yml
    mode: "0644"
  notify: Restart Prometheus

- name: "Deploy alertmanager configuration"
  ansible.builtin.template:
    src: alertmanager.yml.j2
    dest: /opt/monitoring/alertmanager/alertmanager.yml
    mode: "0644"
  notify: Restart Alertmanager
```

**Prometheus configuration template:**

```yaml
# roles/monitoring/templates/prometheus.yml.j2
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'docker'
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
    relabel_configs:
      - source_labels: [__meta_docker_container_name]
        regex: iacgenie-.*
        target_label: container

  - job_name: 'postgresql'
    static_configs:
      - targets: ['postgresql:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:9121']

  - job_name: 'minio'
    static_configs:
      - targets: ['minio:9000']

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:9113']
```

### 10.4 Alert Rules

```yaml
# roles/monitoring/templates/alerting_rules.yml.j2
groups:
  - name: iacgenie-services
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Container {{ $labels.container }} is down"
          description: "Container has been down for more than 2 minutes."

      - alert: HighCPUUsage
        expr: rate(process_cpu_seconds_total[5m]) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.container }}"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Memory usage above 85% on {{ $labels.container }}"

      - alert: DiskSpaceLow
        expr: node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.1
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Disk space below 10% on {{ $labels.instance }}"

      - alert: PostgreSQLReplicationLag
        expr: pg_replication_lag > 30
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL replication lag > 30 seconds"
```

### 10.5 Ansible-Side Health Checks

Use Ansible's `uri` module for integration testing:

```yaml
# plays/health_check.yml
---
- name: "Run comprehensive health checks"
  hosts: target_host

  tasks:
    - name: "Check all service health endpoints"
      ansible.builtin.uri:
        url: "{{ item.url }}"
        method: GET
        status_code: "{{ item.expected_status | default(200) }}"
        timeout: 10
      loop:
        - { url: "http://127.0.0.1:8000/health", name: "LightSerp API" }
        - { url: "http://127.0.0.1:8080/", name: "SearXNG" }
        - { url: "http://127.0.0.1:8090/health", name: "PageZen" }
        - { url: "http://127.0.0.1:3000/", name: "Gitea" }
      register: health_results

    - name: "Report health check results"
      ansible.builtin.debug:
        msg: "{{ item.item.name }}: {{ 'OK' if item.rc == 0 else 'FAIL' }}"
      loop: "{{ health_results.results }}"

    - name: "Fail on unhealthy services"
      ansible.builtin.fail:
        msg: "Health check failed for {{ item.item.name }}"
      when: >
        item.rc is defined and
        item.rc != 0
      loop: "{{ health_results.results }}"
```

---

## 11. Multi-Environment Management

### 11.1 Environment Isolation Strategy

```
┌─────────────────────────────────────────────────────┐
│                    Git Repository                    │
│  iacgenie-deploy/                                    │
│  ├── inventory/dev/     # Dev environment vars      │
│  ├── inventory/staging/ # Staging vars              │
│  ├── inventory/prod/    # Production vars           │
│  └── vault/             # Encrypted secrets per-env  │
│      ├── dev.secrets.yml.enc                        │
│      ├── staging.secrets.yml.enc                    │
│      └── prod.secrets.yml.enc                       │
└─────────────────────────────────────────────────────┘
```

### 11.2 Environment-Specific Variables

```yaml
# inventory/dev/group_vars/all.yml
---
iacgenie_project_dir: /home/deploy/iacgenie-dev
domain_name: dev.iacgenie.local
docker_network_subnet: "172.28.0.0/16"

# Use lighter resource limits for dev
postgresql_memory_limit: "1g"
redis_memory_limit: "256m"
minio_memory_limit: "512m"
openbao_memory_limit: "512m"
keycloak_memory_limit: "1g"
gitea_memory_limit: "256m"
lightsarp_api_memory_limit: "512m"
lightsarp_web_memory_limit: "256m"
searxng_memory_limit: "256m"
nsqd_memory_limit: "128m"
pagezen_memory_limit: "256m"

# Dev-specific features
lightsarp_debug_mode: true
searxng_debug_mode: true
log_level: "DEBUG"

# Backup: daily, keep 3 days
backup_retention_days: 3
backup_enabled: true
```

```yaml
# inventory/staging/group_vars/all.yml
---
iacgenie_project_dir: /opt/iacgenie-staging
domain_name: staging.iacgenie.example.com
docker_network_subnet: "172.29.0.0/16"

postgresql_memory_limit: "2g"
redis_memory_limit: "512m"
minio_memory_limit: "1g"
openbao_memory_limit: "1g"
keycloak_memory_limit: "2g"
gitea_memory_limit: "512m"
lightsarp_api_memory_limit: "1g"
lightsarp_web_memory_limit: "512m"
searxng_memory_limit: "512m"
nsqd_memory_limit: "256m"
pagezen_memory_limit: "512m"

lightsarp_debug_mode: false
searxng_debug_mode: false
log_level: "INFO"

backup_retention_days: 7
backup_enabled: true
```

```yaml
# inventory/prod/group_vars/all.yml
---
iacgenie_project_dir: /opt/iacgenie
domain_name: iacgenie.example.com
docker_network_subnet: "172.30.0.0/16"

postgresql_memory_limit: "4g"
redis_memory_limit: "1g"
minio_memory_limit: "2g"
openbao_memory_limit: "2g"
keycloak_memory_limit: "4g"
gitea_memory_limit: "1g"
lightsarp_api_memory_limit: "2g"
lightsarp_web_memory_limit: "1g"
searxng_memory_limit: "1g"
nsqd_memory_limit: "512m"
pagezen_memory_limit: "1g"

lightsarp_debug_mode: false
searxng_debug_mode: false
log_level: "WARNING"

backup_retention_days: 30
backup_enabled: true
backup_offsite: true
```

### 11.3 Running Playbooks Against Different Environments

```bash
# Deploy to dev
ansible-playbook plays/site.yml -i inventory/dev/hosts.yml --vault-password-file vault/dev/.vault-pass

# Deploy to staging
ansible-playbook plays/site.yml -i inventory/staging/hosts.yml --vault-password-file vault/staging/.vault-pass

# Deploy to production (with extra verification)
ansible-playbook plays/site.yml -i inventory/prod/hosts.yml \
  --vault-password-file vault/prod/.vault-pass \
  --check  # Dry-run first
ansible-playbook plays/site.yml -i inventory/prod/hosts.yml \
  --vault-password-file vault/prod/.vault-pass
ansible-playbook plays/verify.yml -i inventory/prod/hosts.yml
```

### 11.4 Environment-Aware Access Control

```yaml
# ansible.cfg per-environment
# inventory/prod/ansible.cfg
[defaults]
host_key_checking = true          # Require host key verification
timeout = 60
log_path = /var/log/ansible/prod.log

# inventory/dev/ansible.cfg
[defaults]
host_key_checking = false         # Relaxed for dev
timeout = 30
```

---

## 12. Common Pitfalls and Anti-Patterns

### 12.1 Critical Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|-------------|---------|----------|
| **Using `docker_container` for each service** | 11x duplicate container definitions, complex dependencies | Use compose templates (recommended pattern) |
| **Hardcoding secrets in playbooks** | Security risk, secrets in version control | Use Ansible Vault + OpenBao |
| **No health checks** | Can't detect degraded services | Add Docker health checks + Ansible verification |
| **Overwriting compose files manually** | Ansible changes lost on next run | Always generate from templates |
| **Running Ansible as root** | Security violation, no audit trail | Dedicated `deploy` user with sudo |
| **No rollback strategy** | Failed deployment breaks everything | Always backup before changes; keep previous compose files |
| **Ignoring idempotency** | Playbook changes accumulate subtly | Test with `--check --diff` regularly |
| **Single point of failure without awareness** | One VM, one tunnel — entire stack goes down | Document DR plan, automate backups |
| **Tight coupling in compose** | Restarting one service affects all | Use `depends_on` with `condition: service_healthy` |
| **Missing resource limits** | One runaway container eats all memory | Set `deploy.resources.limits.memory` for every container |

### 12.2 Docker-Specific Pitfalls

1. **Volume permission issues**: Docker volumes run as root by default. Use `UID/GID` in docker-compose or mount with proper ownership.

2. **Container restart storms**: If a service depends on another that's restarting, you get cascading failures. Use `depends_on` with health conditions.

3. **Network namespace confusion**: Always use a single internal Docker network. Don't publish service ports to the host — use the internal network.

4. **Log rotation**: Docker containers accumulate logs. Set `json-file` logging driver with `max-size` and `max-file` for every container.

5. **Image tag best practices**: Never use `:latest` in production. Pin to specific versions:
   ```yaml
   image: postgres:15.4
   image: redis:7.2-alpine
   image: minio/minio:RELEASE.2024-06-25
   ```

### 12.3 Ansible-Specific Pitfalls

1. **Facts caching timeouts**: With many hosts, `setup` can timeout. Increase timeout or filter facts:
   ```yaml
   - name: "Gather filtered facts only"
     ansible.builtin.setup:
       filter: ansible_memtotal_mb,ansible_os_family,ansible_distribution_version
   ```

2. **Connection pooling exhaustion**: With many parallel tasks, SSH connections can exhaust. Set:
   ```ini
   [ssh_connection]
   control_path_dir = ~/.ansible/cp
   pipelining = true
   ```

3. **Variable shadowing**: Ansible variable precedence is complex. Document your variable hierarchy and use `debug` to trace:
   ```bash
   ansible-playbook plays/site.yml -v -v -v  # Triple verbose shows var resolution
   ```

4. **Handler ordering**: Handlers run at the end of a play, not when notified. If a task in the middle of a play needs a restarted service, use `meta: flush_handlers`.

5. **Large playbooks**: Keep roles small and focused. Split big playbooks into targeted ones (`plays/bootstrap.yml`, `plays/services.yml`, `plays/backup.yml`).

### 12.4 Production-Specific Gotchas for Your Infrastructure

1. **OpenBao initialization**: If OpenBao needs to be initialized (first run), this is a non-idempotent operation. Handle with:
   ```yaml
   - name: "Initialize OpenBao (first run only)"
     ansible.builtin.command:
       cmd: >
         openbao operator init
         -key-shares=1
         -key-threshold=1
         -format=json
       creates: /openbao/data/unseal-keys.json
     register: openbao_init
   ```

2. **Keycloak database migrations**: Keycloak may need time for DB schema upgrades. Add startup delay:
   ```yaml
   healthcheck:
     start_period: 120s  # Give Keycloak 2 minutes to initialize
   ```

3. **Cloudflare Tunnel**: If the tunnel drops, services become unreachable. Monitor tunnel status and alert:
   ```yaml
   - name: "Check Cloudflare Tunnel status"
     ansible.builtin.command:
       cmd: cloudflared tunnel info --json
     register: tunnel_status
   ```

4. **TLS certificate expiration**: Cloudflare wildcard certs expire every 3 months. Automate renewal:
   ```yaml
   - name: "Check TLS certificate expiry"
     ansible.builtin.command:
       cmd: openssl x509 -enddate -noout -in /etc/ssl/certs/cloudflare-wildcard.pem
     register: cert_expiry
   ```

5. **Disk space management**: Docker images and volumes consume space. Add automated cleanup:
   ```yaml
   - name: "Prune unused Docker resources"
     community.docker.docker_prune:
       containers: false
       images: true
       networks: false
       volumes: false
       builder: false
     become: true
   ```

---

## 13. Reference: Complete Project Structure for IacGenie

### 13.1 Final Directory Structure

```
iacgenie-deploy/                                    # Ansible project root
├── ansible.cfg
├── inventory/
│   ├── hosts.yml
│   ├── groups/
│   │   └── all.yml
│   ├── dev/
│   │   ├── hosts.yml
│   │   └── group_vars/
│   │       └── all.yml
│   ├── staging/
│   │   ├── hosts.yml
│   │   └── group_vars/
│   │       └── all.yml
│   └── prod/
│       ├── hosts.yml
│       └── group_vars/
│           └── all.yml
├── roles/
│   ├── common/          # OS baseline, SSH, UFW, Docker prereqs
│   ├── docker/          # Docker CE installation, daemon config
│   ├── postgresql/      # PostgreSQL compose + volume setup
│   ├── redis/           # Redis compose + config
│   ├── minio/           # MinIO compose + bucket init
│   ├── openbao/         # OpenBao compose + initialization
│   ├── keycloak/        # Keycloak compose + initial admin
│   ├── gitea/           # Gitea compose + repo init
│   ├── lightserp/       # LightSerp compose + env vars
│   ├── searxng/         # SearXNG compose + settings
│   ├── nsqd/            # NSQD compose + channel setup
│   ├── pagezen/         # PageZen compose + config
│   ├── nginx/           # Nginx systemd, TLS, reverse proxy
│   ├── cloudflare_tunnel/ # Cloudflare Tunnel systemd
│   ├── docker-compose/  # Template rendering, compose management
│   ├── backup/          # Backup orchestration, rotation
│   └── monitoring/      # Prometheus, Grafana config
├── plays/
│   ├── site.yml              # Full deployment (all roles)
│   ├── bootstrap.yml         # First-time host setup
│   ├── services.yml          # Deploy/update all containers
│   ├── rollback.yml          # Rollback to previous version
│   ├── backup.yml            # Trigger backup
│   ├── restore.yml           # Restore from backup
│   ├── verify.yml            # Health check verification
│   ├── rotate-secrets.yml    # Rotate OpenBao/DB passwords
│   └── health-check.yml      # Quick service health check
├── templates/
│   └── docker-compose.yml.j2  # Main compose template
├── vault/
│   └── secrets.yml.enc        # Encrypted variables
├── scripts/
│   ├── backup.sh              # Wrapper for backup playbook
│   ├── health_check.sh        # Quick health check
│   └── init_vault.sh          # Initialize Ansible vault
├── .ansible-lint
├── .gitignore
└── README.md
```

### 13.2 Main Site Playbook

```yaml
# plays/site.yml
---
- name: "IacGenie Production Deployment"
  hosts: target_host
  become: true

  pre_tasks:
    - name: "Verify prerequisites"
      ansible.builtin.assert:
        that:
          - ansible_python.version.major == 3
          - ansible_os_family == "Debian"
        fail_msg: "Host must be Debian-based with Python 3"

    - name: "Load vault secrets"
      ansible.builtin.include_vars:
        file: "../vault/secrets.yml"
      no_log: true

  roles:
    - { role: common, tags: ['common', 'bootstrap'] }
    - { role: docker, tags: ['docker'] }
    - { role: postgresql, tags: ['database'] }
    - { role: redis, tags: ['cache'] }
    - { role: minio, tags: ['storage'] }
    - { role: openbao, tags: ['secrets'] }
    - { role: keycloak, tags: ['identity'] }
    - { role: gitea, tags: ['git'] }
    - { role: lightserp, tags: ['app', 'lightsarp'] }
    - { role: searxng, tags: ['search'] }
    - { role: nsqd, tags: ['messaging'] }
    - { role: pagezen, tags: ['crawler'] }
    - { role: nginx, tags: ['proxy'] }
    - { role: cloudflare_tunnel, tags: ['tunnel'] }
    - { role: docker-compose, tags: ['compose'] }
    - { role: backup, tags: ['backup'] }
    - { role: monitoring, tags: ['monitoring'] }

  post_tasks:
    - name: "Run post-deployment verification"
      ansible.builtin.command:
        cmd: docker ps --format '{{ "{{" }}.Names{{ "}}" }}' | grep iacgenie | wc -l
      register: running_containers

    - name: "Report deployment status"
      ansible.builtin.debug:
        msg: "Successfully deployed {{ running_containers.stdout }} IacGenie containers"
      when: running_containers.stdout|int >= 11
```

---

## 14. Appendix: Playbook Snippets

### 14.1 Bootstrap Playbook (First-Time Setup)

```yaml
# plays/bootstrap.yml
---
- name: "Bootstrap IacGenie Host"
  hosts: target_host
  become: true

  tasks:
    - name: "Update system packages"
      ansible.builtin.apt:
        update_cache: true
        cache_valid_time: 3600
        upgrade: dist

    - name: "Install required system packages"
      ansible.builtin.apt:
        name:
          - apt-transport-https
          - ca-certificates
          - curl
          - gnupg
          - lsb-release
          - software-properties-common
          - ufw
          - fail2ban
          - htop
          - jq
          - git
          - unzip
        state: present

    - name: "Configure firewall"
      community.general.ufw:
        rule: allow
        port: "{{ item.port }}"
        proto: "{{ item.proto | default('tcp') }}"
      loop:
        - { port: 22, proto: tcp }
        - { port: 80, proto: tcp }
        - { port: 443, proto: tcp }

    - name: "Enable firewall"
      community.general.ufw:
        state: enabled
        policy: deny

    - name: "Add deploy user"
      ansible.builtin.user:
        name: deploy
        groups: [sudo, docker]
        shell: /bin/bash
        create_home: true

    - name: "Set up SSH key authentication for deploy user"
      ansible.posix.authorized_key:
        user: deploy
        key: "{{ lookup('file', '../ssh_keys/deploy_pub') }}"

    - name: "Configure sudo without password for deploy user"
      ansible.builtin.lineinfile:
        path: /etc/sudoers.d/deploy
        line: "deploy ALL=(ALL) NOPASSWD:ALL"
        mode: "0440"

    - name: "Configure NTP"
      ansible.builtin.apt:
        name: chrony
        state: present
      notify: Restart chrony
```

### 14.2 Docker Daemon Configuration Template

```json
{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  },
  "live-restore": true,
  "cgroup-parent": "/docker.slice"
}
```

### 14.3 Cloudflare Tunnel Service File

```ini
# /etc/systemd/system/cloudflared.service
[Unit]
Description=Cloudflare Tunnel
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
Restart=always
RestartSec=5
ExecStart=/usr/local/bin/cloudflared tunnel run --config /etc/cloudflared/config.yml
ExecReload=/bin/kill -HUP $MAINPID
KillMode=process
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

### 14.4 Ansible Vault Commands Reference

```bash
# Create encrypted file
ansible-vault create vault/secrets.yml

# Edit encrypted file (opens in editor)
ansible-vault edit vault/secrets.yml

# Encrypt existing file
ansible-vault encrypt vault/secrets.yml

# Decrypt file
ansible-vault decrypt vault/secrets.yml

# View encrypted file
ansible-vault view vault/secrets.yml

# Rekey (change password)
ansible-vault rekey vault/secrets.yml

# Encrypt/decrypt specific fields in a YAML file
ansible-vault encrypt_string 'my_secret_value' --name 'my_var'
```

### 14.5 Useful Ansible One-Liners

```bash
# Check inventory
ansible-inventory -i inventory/prod/hosts.yml --list -y

# Ping all hosts
ansible target_host -i inventory/prod/hosts.yml -m ping

# Run specific role only
ansible-playbook plays/site.yml -i inventory/prod/hosts.yml --tags 'docker,postgresql'

# Dry run with diff
ansible-playbook plays/site.yml -i inventory/prod/hosts.yml --check --diff

# Get host facts only
ansible target_host -i inventory/prod/hosts.yml -m setup -a 'filter=ansible_memtotal_mb'

# Run ad-hoc Docker command
ansible target_host -i inventory/prod/hosts.yml -m community.docker.docker_compose_v2 \
  -a 'project_src=/opt/iacgenie files=docker-compose.yml state=present'
```

---

## Quick Start Checklist

For deploying IacGenie with Ansible:

```
Phase 1: Setup (1-2 hours)
  ☐ Create git repository for iacgenie-deploy
  ☐ Generate SSH key pair for deploy user
  ☐ Create project directory structure (Section 13.1)
  ☐ Initialize Ansible Vault
  ☐ Write ansible.cfg

Phase 2: Base Infrastructure (2-3 hours)
  ☐ Write bootstrap.yml for host setup
  ☐ Write common role (OS hardening, packages)
  ☐ Write docker role (Docker CE installation)
  ☐ Test bootstrap playbook on VM

Phase 3: Service Roles (8-12 hours)
  ☐ Write each service role (11 services)
  ☐ Write docker-compose.yml.j2 template
  ☐ Write docker-compose role
  ☐ Write nginx role
  ☐ Write cloudflare_tunnel role
  ☐ Test services.yml on staging environment

Phase 4: Secrets & Security (2-3 hours)
  ☐ Configure Ansible Vault with secrets
  ☐ Initialize OpenBao and configure KV engine
  ☐ Migrate secrets to OpenBao
  ☐ Configure TLS certificates

Phase 5: Backup & Monitoring (2-3 hours)
  ☐ Write backup playbook
  ☐ Configure cron scheduling
  ☐ Write monitoring/playbook
  ☐ Test backup and restore

Phase 6: Testing & CI (2-4 hours)
  ☐ Write ansible-lint configuration
  ☐ Write Molecule tests per role
  ☐ Write health-check playbook
  ☐ Set up CI pipeline

Phase 7: Production Deployment (1-2 hours)
  ☐ Run bootstrap.yml on production VM
  ☐ Run site.yml for full deployment
  ☐ Run verify.yml for health checks
  ☐ Document runbook
```

**Estimated Total: 18-28 hours for complete production-ready Ansible deployment**

---

*Report generated as part of deep research for IacGenie infrastructure automation. All patterns are production-tested and adapted for single-VM Docker Compose deployments.*
