# Ansible and Infrastructure-as-Code Best Practices for Production Deployment of Microservices Infrastructure

**Generated:** 2026-08-01
**Context:** Single Ubuntu 24.04 VM (15GB RAM, 465GB disk) running 11+ Docker services on shared Docker network, exposed via Cloudflare Tunnel through Nginx reverse proxy. Current deployment is manual Docker Compose. Goal: production-ready Ansible IaC.

---

## Table of Contents

1. [Ansible Best Practices](#1-ansible-best-practices)
   1.1 [Project Structure](#11-project-structure)
   1.2 [Inventory Management](#12-inventory-management)
   1.3 [Role Design Patterns](#13-role-design-patterns)
   1.4 [Ansible Vault for Secrets Management](#14-ansible-vault-for-secrets-management)
   1.5 [Ansible Galaxy for Reusable Roles](#15-ansible-galaxy-for-reusable-roles)
   1.6 [Ansible Lint Rules and CI Integration](#16-ansible-lint-rules-and-ci-integration)
   1.7 [Molecule for Testing Playbooks](#17-molecule-for-testing-playbooks)
   1.8 [ansible-pull vs ansible-pull Architecture](#18-ansible-pull-vs-ansible-pull-architecture)
   1.9 [Ansible Navigator and AWX/Ansible Automation Platform](#19-ansible-navigator-and-awxansible-automation-platform)
2. [IaC Best Practices](#2-iac-best-practices)
   2.1 [Infrastructure Versioning and Tracking](#21-infrastructure-versioning-and-tracking)
   2.2 [State Management Patterns](#22-state-management-patterns)
   2.3 [Deployment Order and Dependency Management](#23-deployment-order-and-dependency-management)
   2.4 [Configuration Drift Detection and Remediation](#24-configuration-drift-detection-and-remediation)
   2.5 [Ansible vs Terraform vs Docker Compose Decision Matrix](#25-ansible-vs-terraform-vs-docker-compose-decision-matrix)
   2.6 [When to Use playbooks vs Templates vs copy Modules](#26-when-to-use-playbooks-vs-templates-vs-copy-modules)
   2.7 [System Hardening with Ansible](#27-system-hardening-with-ansible)
   2.8 [Nginx Configuration Management Best Practices](#28-nginx-configuration-management-best-practices)
   2.9 [Docker Compose File Templating and Generation](#29-docker-compose-file-templating-and-generation)
   2.10 [Cloudflare Tunnel Configuration Management](#210-cloudflare-tunnel-configuration-management)
3. [Per-Service Deployment Best Practices](#3-per-service-deployment-best-practices)
   3.1 [PostgreSQL](#31-postgresql)
   3.2 [Redis](#32-redis)
   3.3 [MinIO](#33-minio)
   3.4 [OpenBao](#34-openbao)
   3.5 [Keycloak](#35-keycloak)
   3.6 [Gitea](#36-gitea)
   3.7 [Nginx](#37-nginx)
   3.8 [Cloudflare Tunnel](#38-cloudflare-tunnel)
   3.9 [Docker Compose](#39-docker-compose)
   3.10 [System Hardening](#310-system-hardening)
4. [Recommended Project Structure for IacGenie](#4-recommended-project-structure-for-iacgenie)
5. [CI/CD Pipeline Design](#5-cicd-pipeline-design)
6. [Summary and Recommendations](#6-summary-and-recommendations)

---

## 1. Ansible Best Practices

### 1.1 Project Structure

For a microservices infrastructure with 11+ services, a well-organized project structure is critical. The recommended structure follows the **collections + roles** hybrid approach:

```
iacgenie-ansible/
├── ansible.cfg                  # Ansible configuration
├── inventory/
│   ├── hosts.ini                # Static inventory (single host)
│   ├── group_vars/
│   │   ├── all.yml              # Variables for all hosts
│   │   └── webservers.yml      # Service-specific groups
│   └── host_vars/
│       └── iacgenie-server.yml  # Host-specific variables
├── playbooks/
│   ├── site.yml                 # Master playbook - orchestrates all roles
│   ├── bootstrap.yml            # Initial server setup
│   ├── docker.yml               # Docker installation only
│   ├── services.yml             # Deploy all Docker services
│   ├── validate.yml             # Health checks post-deploy
│   ├── backup.yml               # Backup services
│   └── restore.yml              # Restore from backup
├── roles/
│   ├── common/                  # System hardening, basics
│   │   ├── defaults/main.yml
│   │   ├── vars/main.yml
│   │   ├── tasks/
│   │   │   ├── main.yml
│   │   │   ├── prerequisites.yml
│   │   │   ├── hardening.yml
│   │   │   ├── users.yml
│   │   │   └── cleanup.yml
│   │   ├── handlers/main.yml
│   │   ├── templates/
│   │   ├── files/
│   │   └── meta/main.yml
│   ├── docker/
│   ├── postgresql/
│   ├── redis/
│   ├── minio/
│   ├── openbao/
│   ├── keycloak/
│   ├── gitea/
│   ├── nginx/
│   ├── cloudflare-tunnel/
│   ├── docker-compose-generator/  # Generates docker-compose files
│   └── monitoring/
├── collections/                 # External collection requirements
├── roles/requirements.yml       # Ansible Galaxy role requirements
├── collections/requirements.yml  # Collection requirements
├── ansible-vault/
│   └── secrets.yml              # Encrypted secrets
├── scripts/
│   ├── backup.sh
│   ├── health-check.sh
│   └── restore.sh
├── .github/workflows/
│   ├── ci-lint.yml              # ansible-lint on PR
│   ├── ci-molecule.yml          # Molecule test matrix
│   └── ci-deploy.yml            # Deploy on main branch
├── .ansible-lint                # Ansible-lint configuration
├── .pre-commit-config.yaml      # Pre-commit hooks
├── .env.example                 # Environment variable template
├── Makefile                     # Common commands
├── requirements.txt             # Python dependencies
└── README.md
```

**Key Design Decisions:**

1. **`site.yml` as orchestrator**: Never put business logic in `site.yml`. It should only import/role-call other playbooks or roles in the correct order.

2. **Separation of concerns**: Each service gets its own role with self-contained logic. This enables running `ansible-playbook roles/nginx/tasks/main.yml` independently.

3. **`playbooks/` for compositions**: Create cross-cutting playbooks (`services.yml`, `bootstrap.yml`) that combine roles in correct order.

4. **`inventory/` for data-driven config**: Keep all variable logic in group_vars/host_vars, not in playbooks.

5. **`roles/docker-compose-generator/`**: A special role that renders Jinja2 templates to produce actual `docker-compose.yml` files. This is the key innovation — roles generate compose files rather than having a static compose file.

### 1.2 Inventory Management

For a single-VM deployment, static inventory is sufficient, but design for scale:

```ini
# inventory/hosts.ini
[all:vars]
ansible_user=deploy
ansible_python_interpreter=/usr/bin/python3
ansible_become=yes
ansible_become_method=sudo
ansible_ssh_common_args='-o StrictHostKeyChecking=no'

# Group our single server
[ansible-managed:children]
servers

[servers]
iacgenie-server ansible_host=your.server.ip

# Role-based groups
[docker-hosts]
iacgenie-server

[web-frontend]
iacgenie-server

[database-cluster]
iacgenie-server

[message-queue]
iacgenie-server
```

**Group variables structure:**

```yaml
# inventory/group_vars/all.yml
---
# Common variables
ansible_become: true
ansible_become_method: sudo
timezone: UTC
ntp_servers:
  - 0.pool.ntp.org
  - 1.pool.ntp.org

# Docker settings
docker_compose_version: "2.29.0"
docker_compose_plugin_version: "2.29.0"
docker_network_name: iacgenie-net
docker_network_subnet: "172.28.0.0/16"

# Base resource allocations (per-service defaults, overridden in host_vars)
service_memory_defaults:
  postgres: "2g"
  redis: "512m"
  minio: "4g"
  openbao: "1g"
  keycloak: "2g"
  gitea: "1g"
  nginx: "512m"
  cloudflared: "256m"

# Network configuration
dns_servers:
  - 1.1.1.1
  - 1.0.0.1

# Backup settings
backup_enabled: true
backup_retention_days: 30
backup_schedule: "0 2 * * *"
backup_encryption_enabled: true

# Monitoring
monitoring_enabled: true
prometheus_port: 9090
grafana_port: 3001
```

```yaml
# inventory/host_vars/iacgenie-server.yml
---
# Host-specific overrides
hostname: iacgenie-prod

# PostgreSQL overrides for this host
postgres_max_connections: 200
postgres_shared_buffers: "512MB"
postgres_data_dir: /data/postgres

# Redis overrides
redis_maxmemory: "1gb"
redis_maxmemory_policy: allkeys-lru

# MinIO overrides
minio_root_user: change-me-in-vault
minio_root_password: change-me-in-vault
minio_storage_dir: /data/minio

# Domain configuration
domain: example.com
subdomains:
  web: "app.{{ domain }}"
  dbadmin: "pgadmin.{{ domain }}"
  git: "git.{{ domain }}"
  store: "minio.{{ domain }}"
  vault: "vault.{{ domain }}"
  auth: "auth.{{ domain }}"
```

**Dynamic inventory (future-proofing):** When moving from single-VM to multi-VM:

```yaml
# Dynamic inventory script (Python) for cloud environments
#!/usr/bin/env python3
"""Dynamic inventory for cloud-managed hosts"""
import json
import boto3  # or other cloud SDK

def get_inventory():
    """Query cloud provider for running instances"""
    # Implementation depends on cloud provider
    pass
```

### 1.3 Role Design Patterns

Each role should follow the **one concern per role** principle. Here's the standard role layout with task decomposition:

```
roles/nginx/
├── defaults/main.yml          # Safe defaults, overridable by caller
├── vars/main.yml              # Internal role variables (not overridable)
├── tasks/main.yml             # Entry point - sequential task list
├── tasks/install.yml          # Package installation
├── tasks/configure.yml        # Configuration (templates + copy)
├── tasks/services.yml         # Service management
├── tasks/ssl.yml              # Certificate handling
├── tasks/ssl-renewal.yml      # Let's Encrypt renewal cron
├── handlers/main.yml          # Service reloads, notifications
├── templates/
│   ├── nginx.conf.j2
│   ├── conf.d/upstreams.conf.j2
│   ├── conf.d/reverse-proxy.conf.j2
│   ├── conf.d/security-headers.conf.j2
│   └── snippets/
│       ├── rate-limit.conf.j2
│       ├── geoip.conf.j2
│       └── ssl-params.conf.j2
├── files/
│   ├── nginx.conf.custom      # User override drop-in
│   └── index.html             # Custom error pages
├── meta/main.yml              # Role metadata, dependencies
├── tests/
│   └── test.yml
└── molecule/                  # Molecule testing
```

**Key role design patterns:**

```yaml
# roles/nginx/tasks/main.yml — Pattern: orchestrate sub-tasks
---
- name: Include tasks
  ansible.builtin.include_tasks: "{{ item }}"
  loop:
    - install.yml
    - configure.yml
    - ssl.yml
    - services.yml
  loop_control:
    label: "{{ item }}"
```

```yaml
# roles/nginx/defaults/main.yml — Pattern: comprehensive defaults
---
nginx_package_state: present
nginx_service_state: started
nginx_service_enabled: true
nginx_worker_processes: auto
nginx_worker_connections: 1024
nginx_keepalive_timeout: 65
nginx_client_max_body_size: "100m"
nginx_error_log: /var/log/nginx/error.log
nginx_access_log: /var/log/nginx/access.log
nginx_rate_limit_zone_size: "10m"
nginx_rate_limit_rate: "10r/s"

# Reverse proxy configuration
nginx_enable_reverse_proxy: true
nginx_upstreams:
  - name: keycloak
    servers: "localhost:8080"
    health_check:
      interval: 30
      timeout: 10
  - name: gitea
    servers: "localhost:3000"
    health_check:
      interval: 30
      timeout: 10
  - name: webapp
    servers: "localhost:8081"
    health_check:
      interval: 30
      timeout: 10

# Security settings
nginx_hide_version: true
nginx_ssl_protocols: "TLSv1.2 TLSv1.3"
nginx_ssl_ciphers: "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
nginx_ssl_prefer_server_ciphers: true
nginx_hsts_enabled: true
nginx_hsts_max_age: 31536000
nginx_hsts_include_subdomains: true
```

**Handler design pattern:**

```yaml
# roles/nginx/handlers/main.yml
---
- name: restart nginx
  ansible.builtin.systemd:
    name: nginx
    state: restarted
  listen: "nginx configuration changed"

- name: reload nginx
  ansible.builtin.systemd:
    name: nginx
    state: reloaded
  listen: "nginx configuration changed"

- name: reload nginx ssl
  ansible.builtin.systemd:
    name: nginx
    state: reloaded
  listen: "nginx SSL certificate renewed"
```

**Task conditional pattern for Docker services:**

```yaml
# roles/docker-compose-generator/tasks/main.yml
---
- name: Generate Docker Compose files for each service
  ansible.builtin.template:
    src: "{{ item.service }}.yml.j2"
    dest: "{{ compose_dir }}/{{ item.service }}.yml"
    mode: "0644"
    owner: "{{ compose_owner }}"
    group: "{{ compose_group }}"
  loop: "{{ services_to_deploy }}"
  loop_control:
    label: "{{ item.name }}"
  when: item.deploy | default(true)
  no_log: "{{ no_log_output | default(false) }}"
  notify: restart docker-compose

- name: Validate generated compose files
  community.general.docker_compose_v2:
    project_src: "{{ compose_dir }}"
    files: "{{ item }}"
    state: present
  loop: "{{ compose_files_to_validate }}"
  check_mode: true
  register: compose_validation
  failed_when: false

- name: Fail on invalid compose files
  ansible.builtin.assert:
    that:
      - item.changed | default(false) | not
    fail_msg: "Compose validation failed for {{ item.item }}"
  loop: "{{ compose_validation.results }}"
  when: item.failed | default(false)
```

### 1.4 Ansible Vault for Secrets Management

**Strategy: layered secrets management**

```yaml
# inventory/group_vars/all.yml — reference vault variables
---
# These values are stored in ansible-vault/secrets.yml
# Reference them here as variable lookups

# Database credentials
postgres_password: "{{ vault_postgres_password }}"
postgres_replication_password: "{{ vault_postgres_replication_password }}"
keycloak_admin_password: "{{ vault_keycloak_admin_password }}"

# Application secrets
minio_root_user: "{{ vault_minio_root_user }}"
minio_root_password: "{{ vault_minio_root_password }}"
openbao_root_token: "{{ vault_openbao_root_token }}"
gitea_admin_password: "{{ vault_gitea_admin_password }}"

# Service tokens
cloudflare_api_token: "{{ vault_cloudflare_api_token }}"
cloudflare_tunnel_credentials_file: "{{ vault_cloudflare_tunnel_credentials_json }}"
```

**Vault operations workflow:**

```bash
# Create a new vault
ansible-vault create inventory/group_vars/secrets.yml

# Edit existing vault
ansible-vault edit inventory/group_vars/secrets.yml

# Encrypt an existing file
ansible-vault encrypt inventory/group_vars/old_secrets.yml

# View without decrypting
ansible-vault view inventory/group_vars/secrets.yml

# Decrypt (convert to plaintext — use sparingly)
ansible-vault decrypt inventory/group_vars/secrets.yml

# Run playbook with vault password from file
ansible-playbook playbooks/site.yml --vault-password-file ~/.ansible/vault_pass

# Run with multiple vault passwords
ansible-playbook playbooks/site.yml \
  --vault-password-file ~/.ansible/vault_pass \
  --vault-password-file ~/.ansible/cloudflare_pass
```

**Automation-friendly vault access (CI/CD):**

```bash
# Use environment variable for CI/CD
export ANSIBLE_VAULT_PASSWORD_FILE=~/.ansible/vault_pass

# Or use a remote vault lookup (HashiCorp Vault)
- name: Get secret from Vault
  ansible.builtin.set_fact:
    postgres_password: "{{ lookup('community.hashi_vault.hashi_vault',
        'secret=secret/data/postgres:password
        url=https://vault.example.com:8200
        token=...' | companyEqual }}</string>
```

**Secret rotation strategy:**

```yaml
# roles/common/tasks/rotate-secrets.yml
---
- name: Generate new random password for service
  ansible.builtin.set_fact:
    new_password: "{{ lookup('community.general.password', '/dev/null length=32 chars=ascii_letters,digits') }}"

- name: Store new password in vault
  ansible.builtin.shell: |
    ansible-vault encrypt_string '{{ new_password }}' --name 'vault_service_password'
  register: vault_output

- name: Display new encrypted value for manual update
  ansible.builtin.debug:
    msg: "Update the vault entry with: {{ vault_output.stdout_lines[0] }}"
```

**Best Practices Summary:**

1. **Never commit vault contents** to git. Add `*.yml` under `secrets/` to `.gitignore`.
2. **Use separate vault files** per concern (DB secrets, service tokens, SSH keys).
3. **Use environment variables** in CI/CD (`ANSIBLE_VAULT_PASSWORD_FILE`).
4. **Audit vault access** with `ansible-vault view` logging.
5. **Rotate secrets regularly** — document rotation schedule.
6. **Use HashiCorp Vault** or AWS Secrets Manager for production at scale.

### 1.5 Ansible Galaxy for Reusable Roles

**Role requirements (`roles/requirements.yml`):**

```yaml
---
roles:
  - name: geerlingguy.docker
    version: "6.1.0"
  - name: geerlingguy.nginx
    version: "3.4.1"
  - name: geerlingguy.postgres
    version: "3.5.0"
  - name: geerlingguy.redis
    version: "2.6.0"
  - name: geerlingguy.certbot
    version: "4.1.0"

collections:
  - name: ansible.posix
    version: ">=1.5.0"
  - name: community.general
    version: ">=8.0.0"
  - name: community.docker
    version: ">=3.4.0"
  - name: ansible.posix
    version: ">=1.5.0"
  - name: ansible.utils
    version: ">=3.0.0"
  - name: community.hashi_vault
    version: ">=1.0.0"
```

**Install all requirements:**

```bash
ansible-galaxy install -r roles/requirements.yml
ansible-galaxy collection install -r collections/requirements.yml
```

**When to use Galaxy roles vs custom roles:**

| Scenario | Approach | Rationale |
|----------|----------|-----------|
| Install Docker | Galaxy role (geerlingguy.docker) | Battle-tested, well-maintained |
| Install Nginx | **Custom role** | Need deep template control for reverse proxy |
| Install PostgreSQL | **Custom role** | Deep config control needed |
| System hardening | **Custom role** | CIS benchmark specific |
| Docker compose | **Custom role** | Domain-specific compose generation |
| Basic SSH config | Galaxy role (geerlingguy.openssh) | Standard hardening patterns |

**Publishing custom roles to Galaxy:**

```bash
# Initialize role structure
ansible-galaxy role init roles/my-custom-role

# Push to Galaxy (if published)
ansible-galaxy role publish --token $ANSIBLE_GALAXY_TOKEN

# Or use private role repositories for internal roles
ansible-galaxy role install git+https://git.example.com/team/ansible-role-common.git
```

### 1.6 Ansible Lint Rules and CI Integration

**`.ansible-lint` configuration:**

```yaml
---
# .ansible-lint
profile: production

skip_list:
  - yaml[line-length]          # Long lines in templates are ok
  - yaml[truthy]               # Sometimes we need bare "yes"
  - no-changed-when            # Some modules always report changed
  - command-instead-of-shell   # Acceptable for system commands
  - risky-shell-pipe           # We handle pipe safety manually

warn_list:
  - no-handler                   # Prefer notify over handler in some cases
  - risky-file-permissions       # Audit file permission checks
  - var-naming[no-role-prefix]  # Prefix role variables
  - git-latest                   # Use explicit versions in git roles
  - name[missing]               # All tasks should have names

exclude_paths:
  - .github/
  - tests/
  - molecule/

roles_path:
  - roles/
  - collections/ansible_collections

merge_handling_rules:
  jinja_spacing: "no_space"

parsed_dependencies:
  - requirements.yml
  - collections/requirements.yml
```

**CI Pipeline (GitHub Actions):**

```yaml
# .github/workflows/ci-lint.yml
name: Ansible Lint CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ansible-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install requirements
        run: |
          pip install ansible-lint ansible-core
          ansible-galaxy install -r roles/requirements.yml
          ansible-galaxy collection install -r collections/requirements.yml

      - name: Run ansible-lint
        run: ansible-lint

      - name: Validate YAML syntax
        run: |
          find . -name "*.yml" -not -path "./.git/*" | xargs -I {} python -c "
            import yaml, sys
            yaml.safe_load(open('{}'))
          " || exit 1

      - name: Validate Jinja2 templates
        run: |
          find roles -name "*.j2" | while read f; do
            ansible-inventory --list 2>/dev/null > /dev/null || true
            ansible-playbook --syntax-check -i "localhost," playbooks/validate.yml 2>/dev/null || true
          done
```

### 1.7 Molecule for Testing Playbooks

**Molecule example for a Docker service role:**

```yaml
# roles/docker-compose-generator/molecule/default/molecule.yml
---
dependency:
  name: galaxy
driver:
  name: delegated
platforms:
  - name: ubuntu-server
    image: ubuntu:24.04
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    privileged: true
    pre_build_image: true
provisioner:
  name: ansible
verifier:
  name: ansible
```

```yaml
# roles/docker-compose-generator/molecule/default/converge.yml
---
- name: Converge
  ansible.builtin.import_playbook: ../../playbooks/converge.yml
```

```yaml
# roles/docker-compose-generator/molecule/default/verify.yml
---
- name: Verify
  ansible.builtin.import_playbook: ../../molecule/default/tests.yml
```

```yaml
# roles/docker-compose-generator/molecule/default/tests.yml
---
- name: Verify generated compose files
  hosts: all
  tasks:
    - name: Check compose files exist
      ansible.builtin.stat:
        path: "/opt/docker/{{ item }}"
      loop:
        - postgres.yml
        - redis.yml
        - minio.yml
        - openbao.yml
        - keycloak.yml
        - gitea.yml
      register: compose_files

    - name: Assert all compose files were generated
      ansible.builtin.assert:
        that:
          - item.stat.exists
        fail_msg: "Compose file {{ item.item }} was not generated"
      loop: "{{ compose_files.results }}"

    - name: Validate YAML syntax of generated files
      ansible.builtin.shell: python3 -c "import yaml; yaml.safe_load(open('{{ item }}'))"
      loop:
        - /opt/docker/postgres.yml
        - /opt/docker/redis.yml
        - /opt/docker/minio.yml
      register: yaml_validation

    - name: Assert YAML validity
      ansible.builtin.assert:
        that:
          - item.rc == 0
      loop: "{{ yaml_validation.results }}"

    - name: Check compose files contain expected services
      ansible.builtin.shell: |
        grep -q "image:" "{{ item }}"
      loop:
        - /opt/docker/postgres.yml
        - /opt/docker/redis.yml
      register: service_check

    - name: Assert services are defined
      ansible.builtin.assert:
        that:
          - item.rc == 0
      loop: "{{ service_check.results }}"
```

**Running Molecule:**

```bash
# Run all molecule tests for a role
cd roles/docker-compose-generator
molecule test

# Run converge only
molecule converge

# Run destroy then converge
molecule destroy && molecule converge

# Run specific scenario
molecule test -s default

# Dry-run to validate without provisioning
molecule converge --destroy=never
```

### 1.8 ansible-pull vs ansible-pull Architecture

**ansible-pull** is an agentless model where each node pulls configuration from a central Git repo. For a **single-VM deployment**, this is overkill. However, understanding the trade-offs is important:

| Aspect | ansible-push (traditional) | ansible-pull |
|--------|---------------------------|--------------|
| Model | Central controller pushes to nodes | Nodes pull from Git |
| Scale | Limited by controller capacity | Scales to thousands of nodes |
| Security | Controller has SSH access to all nodes | Nodes are behind firewall |
| Complexity | Simple setup | Requires Jenkins/puppet-server or Git |
| Idempotency | Push-based execution | Cron-driven, periodic |
| Audit trail | Centralized logs | Git history is audit trail |
| Best for | Small teams, single/multi-VM | Large-scale, distributed |

**Recommendation for IacGenie:** Use **ansible-push** (traditional push model). The single-VM setup makes ansible-pull unnecessary. The push model gives you:
- Immediate execution when changes are needed
- Easier debugging (centralized errors)
- Simpler CI/CD integration
- No need for pull-server infrastructure

If you later scale to multi-VM, ansible-pull becomes more attractive.

### 1.9 Ansible Navigator and AWX/Ansible Automation Platform

**Ansible Navigator** — for interactive development and debugging:

```bash
# Install
pip install ansible-navigator

# Run playbook with interactive UI
ansible-navigator run playbooks/site.yml

# Run with specific inventory
ansible-navigator run playbooks/site.yml -i inventory/hosts.ini

# Run in terminal mode (no ncurses)
ansible-navigator run playbooks/site.yml --mode stdout

# Peek at a playbook
ansible-navigator peek playbooks/site.yml

# Run as standalone command
ansible-navigator

# Configure globally
ansible-navigator configure
```

**Ansible Navigator Config (`ansible-navigator.yml`):**

```yaml
---
ansible-navigator:
  execution-environment:
    enabled: false
  logging:
    level: debug
    file: ansible-navigator.log
  playbook: playbooks/site.yml
  inventory:
    - inventory/hosts.ini
  modes:
    - run
    - stand-alone
    - playbook-detail
    - doc-plugin
    - dump-playbook
    - execute
    - wallop
```

**AWX/Ansible Automation Platform** — for teams and production orchestration:

For a single-VM setup, AWX is **overkill**. Consider it when:
- Multiple people need to manage infrastructure
- You need RBAC (role-based access control)
- You need scheduling, approvals, and audit trails
- You manage 10+ hosts

**AWX deployment on same VM** (if needed):

```yaml
# roles/awx/tasks/main.yml (simplified)
---
- name: Install AWX dependencies
  ansible.builtin.apt:
    name:
      - postgresql
      - redis
      - docker
      - docker-compose
    state: present

- name: Deploy AWX via AWX Operator
  ansible.builtin.include_role:
    name: ansible.awx.awx
```

---

## 2. IaC Best Practices

### 2.1 Infrastructure Versioning and Tracking

**Git-based versioning is the foundation of IaC:**

```
iacgenie-ansible/
├── .git/
│   ├── .gitignore
│   └── COMMIT_MESSAGE.md    # Conventional commit guidelines
├── CHANGELOG.md
├── VERSION                    # Current version
└── .github/
    └── workflows/
        ├── ci-lint.yml
        ├── ci-molecule.yml
        └── ci-deploy.yml
```

**Branching strategy:**

```
main
├── develop
│   ├── feature/nginx-hardening
│   ├── feature/postgresql-tuning
│   ├── feature/backup-automation
│   └── hotfix/ssl-expiry
└── release/v1.2.0
```

**Version tracking in Ansible:**

```yaml
# roles/docker-compose-generator/defaults/main.yml
---
# Version tracking metadata
iacgenie_version: "1.2.0"
iacgenie_release_date: "2026-08-01"
iacgenie_ansible_min_version: "2.15"
iacgenie_services_version:
  postgres: "16.4"
  redis: "7.2"
  minio: "2024"
  openbao: "1.16"
  keycloak: "25.0"
  gitea: "1.22"
  nginx: "1.26"
  cloudflared: "2024"
```

**Tags and releases:**

```bash
# Tag infrastructure changes
git tag -a v1.2.0 -m "Infrastructure v1.2.0: Keycloak upgrade, MinIO erasure coding"
git push origin v1.2.0

# View infrastructure changes since last release
git log v1.1.0..v1.2.0 --oneline
```

### 2.2 State Management Patterns

**Ansible vs Terraform state:** Ansible is **idempotent by design** — it doesn't maintain state files. This is a key advantage:

```
State Management Approaches:
───────────────────────────

Ansible (no external state):
  - Idempotent: re-running produces same result
  - No state file to corrupt or drift
  - Deterministic: task order = execution order
  - Can be slow on large systems (gathers facts each run)

Terraform (external state file):
  - terraform.state tracks resource mapping
  - State can become corrupted
  - Requires state locking for teams
  - Powerful drift detection
  - Great for cloud resources (AWS, GCP, Azure)

For IacGenie:
  ✓ Ansible alone is sufficient (no cloud resources)
  ✓ No external state management needed
  ✓ Deterministic, auditable, simple
  ✓ Docker compose files are the "state" (declared)
```

**Filesystem as state:** Docker Compose files themselves serve as the desired state. The compose files are templates rendered by Ansible. Running `docker compose up -d` makes the actual state match the declared state.

**Idempotency verification:**

```yaml
# Verify idempotency with check mode
ansible-playbook playbooks/site.yml --check --diff

# --check: Don't make changes, report what would change
# --diff: Show what would change in files
```

### 2.3 Deployment Order and Dependency Management

**Service dependency graph for IacGenie:**

```
Service Dependency Order:

1. BASE LAYER (Infrastructure)
   ├── System hardening
   ├── Docker + Docker Compose
   └── Cloudflare Tunnel (network foundation)

2. DATA LAYER
   ├── PostgreSQL (primary storage)
   └── Redis (caching/session)

3. SECURITY LAYER
   └── OpenBao (secrets/vault)

4. APPLICATION LAYER
   ├── Keycloak (authentication)
   └── MinIO (object storage)

5. COLLABORATION LAYER
   └── Gitea (Git hosting)

6. ACCESS LAYER
   └── Nginx (reverse proxy)
```

```yaml
# playbooks/site.yml
---
- name: Deploy IacGenie Infrastructure
  hosts: iacgenie-server
  become: true
  gather_facts: true

  pre_tasks:
    - name: Verify system requirements
      ansible.builtin.assert:
        that:
          - ansible_memtotal_mb >= 10240
          - ansible_availdistro is defined
        fail_msg: "System does not meet minimum requirements"

  roles:
    # 1. Base infrastructure
    - role: roles/common
      tags: [common, base]
    - role: roles/docker
      tags: [docker, base]

    # 2. Data layer
    - role: roles/postgresql
      tags: [database, data]
    - role: roles/redis
      tags: [cache, data]

    # 3. Security layer
    - role: roles/openbao
      tags: [security, vault]
      become: false   # Run as non-root where possible

    # 4. Application layer
    - role: roles/keycloak
      tags: [auth, app]
    - role: roles/minio
      tags: [storage, app]

    # 5. Collaboration layer
    - role: roles/gitea
      tags: [git, app]

    # 6. Access layer
    - role: roles/nginx
      tags: [nginx, proxy]
    - role: roles/docker-compose-generator
      tags: [compose, generator]

    # 7. Post-deploy
    - role: roles/monitoring
      tags: [monitoring, post-deploy]
      when: monitoring_enabled | default(true)

  post_tasks:
    - name: Validate all services are running
      ansible.builtin.include_tasks: tasks/validate.yml

    - name: Generate deployment summary
      ansible.builtin.debug:
        msg: "Deployment completed successfully"
```

### 2.4 Configuration Drift Detection and Remediation

**Drift detection strategies:**

```yaml
# roles/common/tasks/drift-detection.yml
---
- name: Check for configuration drift
  ansible.builtin.include_tasks: check-drift.yml

- name: Generate drift report
  ansible.builtin.template:
    src: drift-report.yml.j2
    dest: /opt/monitoring/drift-report-{{ ansible_date_time.iso8601 }}.yml
    mode: "0644"

- name: Report drift findings
  ansible.builtin.debug:
    msg: "Drift detected: {{ drift_findings }}"
  when: drift_findings | default([]) | length > 0
```

**Continuous drift detection with cron:**

```bash
# Add to /etc/crontab via Ansible
# Check for drift every 6 hours
0 */6 * * * deploy /opt/scripts/drift-check.sh >> /var/log/ansible-drift.log 2>&1
```

**drift-check.sh:**

```bash
#!/bin/bash
# Drift detection script
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DRIFT_FILE="/opt/monitoring/drift-${TIMESTAMP}.json"

# Check critical file modifications
find /etc/nginx /etc/postgresql /etc/redis \
  -newer /opt/ansible/.last-deploy -type f \
  -exec ls -la {} \; > "${DRIFT_FILE}" 2>&1

# Check Docker service state
docker compose -f /opt/docker/docker-compose.yml ps \
  --format json > /tmp/docker-status.json 2>&1

# Send alert if drift detected
if [ -s "${DRIFT_FILE}" ]; then
    curl -s -X POST "${SLACK_WEBHOOK_URL}" \
      -H 'Content-Type: application/json' \
      -d "{\"text\": \"⚠️ Configuration drift detected at ${TIMESTAMP}\"}"
fi
```

**Remediation approach:** Always fix drift by **re-running the playbook**, not by manual intervention. Manual changes should be immediately captured in the Ansible codebase.

### 2.5 Ansible vs Terraform vs Docker Compose Decision Matrix

| Concern | Docker Compose | Ansible | Terraform | Recommendation for IacGenie |
|---------|---------------|---------|-----------|------------------------------|
| Container lifecycle | ✅ Native | ❌ Via collection | ❌ Via provider | Docker Compose for containers |
| System packages | ❌ | ✅ Native | ⚠️ Via provider | Ansible for system setup |
| Network config | ✅ | ✅ | ✅ | Docker Compose for internal nets |
| Storage volumes | ✅ | ⚠️ Basic | ✅ | Docker Compose for volumes |
| Firewall | ❌ | ✅ | ⚠️ Cloud-specific | Ansible for local firewall |
| SSL/TLS | ❌ | ⚠️ Via certbot | ✅ | Ansible + certbot |
| Secrets | ❌ | ✅ (Vault) | ✅ (Vault provider) | Ansible Vault |
| Idempotency | ❌ | ✅ Native | ✅ State-based | Ansible (single source of truth) |
| Multi-host | ⚠️ Swarm/K8s | ✅ Excellent | ✅ Excellent | Ansible for 1-50 hosts |
| Cloud provisioning | ❌ | ⚠️ Via modules | ✅ Native | N/A (single VM) |
| Learning curve | Low | Medium | High | Ansible is sufficient |
| GitOps-friendly | Moderate | ✅ High | ✅ High | Ansible integrates with GitOps |
| Cost | Free | Free | Free | All free |

**IacGenie Architecture Decision:**

```
Use all three, but with clear separation:

1. Ansible (Primary IaC):
   - System hardening, package management
   - Service configuration (Nginx, databases)
   - Secrets management (Vault)
   - Orchestration of all other tools
   - User management, SSH config

2. Docker Compose (Generated by Ansible):
   - Container lifecycle management
   - Network configuration between containers
   - Volume management
   - Health checks, restart policies

3. Cloudflare Tunnel (Configured via Ansible):
   - External traffic routing
   - SSL termination at Cloudflare edge
   - Zero-trust network access

Ansible IS the orchestrator that manages everything.
```

### 2.6 When to Use playbooks vs Templates vs copy Modules

```
Decision Guide:

┌─────────────────────────────────┬──────────────┬──────────────┐
│ Need                            │ Ansible Copy │ Jinja2       │
│                                 │ Module       │ Template     │
├─────────────────────────────────┼──────────────┼──────────────┤
│ Fixed config, never changes     │ ✅ Copy      │ ❌ Overkill  │
│ Config varies per environment   │ ❌ No        │ ✅ Template  │
│ Binary files (certs, archives)  │ ✅ Copy      │ ❌ No        │
│ Partial file sections           │ ✅ Block    │ ✅ Template  │
│ Dynamic content from vars       │ ❌ No        │ ✅ Template  │
│ Multiple files from data        │ ❌ No        │ ✅ Template  │
│ Simple file copy with owner     │ ✅ Copy      │ ❌ Overkill  │
│ Conditional content             │ ❌ No        │ ✅ Template  │
│ Loops over data structures      │ ❌ No        │ ✅ Template  │
└─────────────────────────────────┴──────────────┴──────────────┘

Rule of thumb:
- Use copy for: certs, keys, binaries, static files
- Use template for: configs with variables, conditionals, loops
- Use blockinfile for: adding sections to existing files
- Use lineinfile for: single-line modifications
```

### 2.7 System Hardening with Ansible

**CIS Benchmark Compliance for Ubuntu 24.04:**

```yaml
# roles/common/tasks/hardening.yml
---
- name: Configure SSH hardening
  ansible.builtin.lineinfile:
    path: /etc/ssh/sshd_config
    regexp: "{{ item.regexp }}"
    line: "{{ item.line }}"
    validate: "sshd -t -f %s"
    notify: restart sshd
  loop:
    - regexp: "^#?PermitRootLogin"
      line: "PermitRootLogin prohibit-password"
    - regexp: "^#?PasswordAuthentication"
      line: "PasswordAuthentication no"
    - regexp: "^#?PubkeyAuthentication"
      line: "PubkeyAuthentication yes"
    - regexp: "^#?MaxAuthTries"
      line: "MaxAuthTries 3"
    - regexp: "^#?X11Forwarding"
      line: "X11Forwarding no"
    - regexp: "^#?AllowUsers"
      line: "AllowUsers {{ ssh_allowed_users | join(' ') }}"
    - regexp: "^#?ClientAliveInterval"
      line: "ClientAliveInterval 300"
    - regexp: "^#?ClientAliveCountMax"
      line: "ClientAliveCountMax 2"

- name: Configure firewall rules
  ansible.posix.ufw:
    rule: "{{ item.rule }}"
    port: "{{ item.port }}"
    proto: "{{ item.proto | default('tcp') }}"
  loop: "{{ ufw_rules }}"
  notify: restart ufw

- name: Configure fail2ban
  ansible.builtin.template:
    src: jail.local.j2
    dest: /etc/fail2ban/jail.local
    mode: "0600"
    owner: root
    group: root
  notify: restart fail2ban

- name: Configure logrotate
  ansible.builtin.template:
    src: logrotate.conf.j2
    dest: /etc/logrotate.d/iacgenie
    mode: "0644"
  notify: reload logrotate
```

**UFW firewall rules:**

```yaml
# roles/common/defaults/main.yml
---
# UFW configuration
ufw_default_policy: deny
ufw_rules:
  - rule: allow
    port: "22"
    proto: tcp
    comment: "SSH access"
  - rule: allow
    port: "80"
    proto: tcp
    comment: "HTTP redirect"
  - rule: allow
    port: "443"
    proto: tcp
    comment: "HTTPS via Cloudflare"
  - rule: deny
    port: "3000"
    proto: tcp
    comment: "Gitea internal only"
  - rule: deny
    port: "5432"
    proto: tcp
    comment: "PostgreSQL internal only"
  - rule: deny
    port: "6379"
    proto: tcp
    comment: "Redis internal only"
  - rule: deny
    port: "9000"
    proto: tcp
    comment: "MinIO internal only"
```

### 2.8 Nginx Configuration Management Best Practices

**Key principles for Nginx in a microservices setup:**

1. **Use include directives** for modular configuration
2. **Template all Nginx config** — never static copy
3. **Rate limiting per upstream** to prevent cascade failures
4. **Separate security headers** into their own included file
5. **Use upstream blocks** for health checking and load balancing
6. **Disable server tokens** and minimize exposed information
7. **SSL parameters from Mozilla SSL Configuration Generator**

```yaml
# roles/nginx/templates/nginx.conf.j2
user www-data;
worker_processes {{ nginx_worker_processes | default('auto') }};
pid /run/nginx.pid;
error_log {{ nginx_error_log }} warn;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections {{ nginx_worker_connections | default(1024) }};
    multi_accept on;
}

http {
    # Basic settings
    sendfile on;
    tcp_nopush on;
    types_hash_max_size 2048;
    {{ 'server_tokens off;' if nginx_hide_version | default(true) }}
    server_names_hash_bucket_size {{ nginx_server_names_hash_bucket_size | default(64) }};

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request_method $request_uri"'
                    '$status $body_bytes_sent "$http_referer"'
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log {{ nginx_access_log }} main;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general:{{ nginx_rate_limit_zone_size | default('10m') }} rate={{ nginx_rate_limit_rate | default('10r/s') }};
    limit_req_zone $binary_remote_addr zone=api:{{ nginx_rate_limit_api_zone_size | default('10m') }} rate={{ nginx_rate_limit_api_rate | default('5r/s') }};

    # Proxy settings
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # SSL parameters (Mozilla recommended)
    ssl_protocols {{ nginx_ssl_protocols | default('TLSv1.2 TLSv1.3') }};
    ssl_ciphers {{ nginx_ssl_ciphers | default('ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384') }};
    ssl_prefer_server_ciphers {{ 'on' if nginx_ssl_prefer_server_ciphers | default(true) else 'off' }};
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
```

**Security headers template:**

```nginx
# roles/nginx/templates/conf.d/security-headers.conf.j2
# Security Headers
add_header X-Frame-Options "{{ nginx_xframe_options | default('SAMEORIGIN') }}" always;
add_header X-Content-Type-Options "{{ nginx_xcontent_type | default('nosniff') }}" always;
add_header X-XSS-Protection "{{ nginx_xxss | default('1; mode=block') }}" always;
{% if nginx_hsts_enabled | default(true) %}
add_header Strict-Transport-Security "max-age={{ nginx_hsts_max_age | default(31536000) }};{% if nginx_hsts_include_subdomains | default(true) %}includeSubDomains{% endif %};{% if nginx_hsts_preload | default(false) %}preload{% endif %}" always;
{% endif %}
add_header Referrer-Policy "{{ nginx_referrer_policy | default('strict-origin-when-cross-origin') }}" always;
add_header Content-Security-Policy "{{ nginx_csp | default(\"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'\") }}" always;
add_header Permissions-Policy "{{ nginx_permissions_policy | default('camera=(), microphone=(), geolocation=()') }}" always;
```

### 2.9 Docker Compose File Templating and Generation

**This is the critical innovation for Ansible-managed Docker infrastructure:**

```yaml
# roles/docker-compose-generator/templates/postgres.yml.j2
version: "3.9"

services:
  postgres:
    image: postgres:{{ postgres_version | default('16') }}-alpine
    container_name: iacgenie-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: "{{ postgres_user }}"
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      POSTGRES_DB: "{{ postgres_database }}"
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --locale=C"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - postgres_backup:/backup
      - ./scripts/backup.sh:/scripts/backup.sh:ro
    secrets:
      - postgres_password
    ports:
      - "127.0.0.1:5432:5432"
    networks:
      - iacgenie-net
      - internal-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U {{ postgres_user }} -d {{ postgres_database }}"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    deploy:
      resources:
        limits:
          memory: {{ service_memory_defaults.postgres }}
          cpus: "2.0"
        reservations:
          memory: 512M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    # Security
    read_only: true
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp
      - /run/postgresql

volumes:
  postgres_data:
    name: iacgenie-postgres-data
  postgres_backup:
    name: iacgenie-postgres-backup

secrets:
  postgres_password:
    file: /opt/secrets/postgres_password
```

**Generate compose files for ALL services:**

```yaml
# roles/docker-compose-generator/tasks/main.yml
---
- name: Create Docker compose directory
  ansible.builtin.file:
    path: "{{ compose_dir }}"
    state: directory
    mode: "0755"
    owner: "{{ compose_owner }}"
    group: "{{ compose_group }}"

- name: Copy helper scripts
  ansible.builtin.copy:
    src: "{{ item }}"
    dest: "{{ compose_dir }}/scripts/{{ item }}"
    mode: "0755"
    owner: "{{ compose_owner }}"
    group: "{{ compose_group }}"
  loop:
    - backup.sh
    - health-check.sh

- name: Generate service compose files
  ansible.builtin.template:
    src: "{{ item }}.yml.j2"
    dest: "{{ compose_dir }}/{{ item }}.yml"
    mode: "0644"
    owner: "{{ compose_owner }}"
    group: "{{ compose_group }}"
  loop: "{{ compose_services }}"

- name: Generate master compose file
  ansible.builtin.template:
    src: docker-compose.yml.j2
    dest: "{{ compose_dir }}/docker-compose.yml"
    mode: "0644"
    owner: "{{ compose_owner }}"
    group: "{{ compose_group }}"
```

### 2.10 Cloudflare Tunnel Configuration Management

**cloudflared configuration via Ansible:**

```yaml
# roles/cloudflare-tunnel/defaults/main.yml
---
cloudflared_version: "2024.12.0"
cloudflared_user: cloudflared
cloudflared_config_dir: /etc/cloudflared
cloudflared_log_dir: /var/log/cloudflared
cloudflared_tunnel_id: "{{ vault_cloudflared_tunnel_id | default('') }}"
cloudflared_credentials_file: "{{ cloudflared_config_dir }}/creds.json"

cloudflared_tunnel_name: "iacgenie-prod"
cloudflared_listen_port: 3000

# Tunnel routing rules
cloudflared_routes:
  - path: "/"
    service: http://nginx:80
  - path: "/.well-known/acme-challenge/*"
    service: http://nginx:80

cloudflared_log_level: info
cloudflared_log_dir: "{{ cloudflared_log_dir }}"
cloudflared_metrics_enabled: true
```

```yaml
# roles/cloudflare-tunnel/tasks/main.yml
---
- name: Create cloudflared user
  ansible.builtin.user:
    name: "{{ cloudflared_user }}"
    system: true
    shell: /usr/sbin/nologin
    create_home: false

- name: Create configuration directories
  ansible.builtin.file:
    path: "{{ item }}"
    state: directory
    mode: "0755"
    owner: "{{ cloudflared_user }}"
    group: "{{ cloudflared_user }}"
  loop:
    - "{{ cloudflared_config_dir }}"
    - "{{ cloudflared_log_dir }}"

- name: Download cloudflared binary
  ansible.builtin.get_url:
    url: "https://github.com/cloudflare/cloudflared/releases/{{ cloudflared_version }}/cloudflared-linux-amd64"
    dest: "/usr/local/bin/cloudflared"
    mode: "0755"
    checksum: "sha256:{{ vault_cloudflared_binary_sha256 }}"

- name: Deploy tunnel credentials (from vault)
  ansible.builtin.copy:
    content: "{{ vault_cloudflare_tunnel_credentials_json }}"
    dest: "{{ cloudflared_credentials_file }}"
    mode: "0600"
    owner: "{{ cloudflared_user }}"
    group: "{{ cloudflared_user }}"

- name: Deploy cloudflared service configuration
  ansible.builtin.template:
    src: cloudflared.service.j2
    dest: /etc/systemd/system/cloudflared.service
    mode: "0644"
  notify: restart cloudflared

- name: Enable and start cloudflared
  ansible.builtin.systemd:
    name: cloudflared
    state: started
    enabled: true
```

**cloudflared service template:**

```ini
# roles/cloudflare-tunnel/templates/cloudflared.service.j2
[Unit]
Description=Cloudflare Tunnel
Documentation=https://developers.cloudflare.com/cloudflare-one/
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
User={{ cloudflared_user }}
Group={{ cloudflared_user }}
ExecStart=/usr/local/bin/cloudflared tunnel --no-autoupdate run \
    --config {{ cloudflared_config_dir }}/config.yml \
    --metrics {{ cloudflared_metrics_enabled | default(true) | ternary('0.0.0.0:{{ vault_cloudflared_metrics_port | default(2000) }}', 'off') }} \
    --log {{ cloudflared_log_dir }}/cloudflared.log \
    --logfile {{ cloudflared_log_dir }}/cloudflared.log
Restart=on-failure
RestartSec=5

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths={{ cloudflared_config_dir }} {{ cloudflared_log_dir }} /tmp

[Install]
WantedBy=multi-user.target
```

---

## 3. Per-Service Deployment Best Practices

### 3.1 PostgreSQL

**Ansible Role: `roles/postgresql`**

```yaml
# roles/postgresql/defaults/main.yml
---
postgres_version: "16"
postgres_user: "iacgenie"
postgres_password: "{{ vault_postgres_password }}"
postgres_database: "iacgenie"
postgres_max_connections: 200
postgres_shared_buffers: "512MB"
postgres_effective_cache_size: "1536MB"
postgres_work_mem: "16MB"
postgres_maintenance_work_mem: "128MB"
postgres_wal_level: "replica"
postgres_max_wal_size: "2GB"
postgres_min_wal_size: "80MB"
postgres_checkpoint_completion_target: 0.9
postgres_checkpoint_timeout: "10min"
postgres_autovacuum_max_workers: 3
postgres_autovacuum_naptime: "30s"
postgres_autovacuum_vacuum_threshold: 50
postgres_autovacuum_analyze_threshold: 50
postgres_autovacuum_vacuum_scale_factor: 0.1
postgres_autovacuum_analyze_scale_factor: 0.05
postgres_hot_standby: "off"
postgres_log_destination: "stderr"
postgres_logging_collector: "on"
postgres_log_directory: "/var/log/postgresql"
postgres_log_filename: "postgresql-%Y-%m-%d.log"
postgres_log_min_duration_statement: 1000
postgres_log_lock_waits: "on"
postgres_log_statement: "ddl"
```

**Key configuration practices:**

| Aspect | Best Practice | Rationale |
|--------|--------------|-----------|
| Connection pooling | pgbouncer in front of PostgreSQL | Reduces connection overhead, protects against connection storms |
| WAL archiving | Configure `archive_command` for point-in-time recovery | Enables backup recovery |
| Shared buffers | 25% of available RAM for dedicated DB servers | More on shared VM: use 1/4 of allocated memory |
| Work mem | 8-16MB for general workloads | Per-operation memory, don't set too high |
| Autovacuum | Tune for write-heavy workloads | Prevent table bloat and performance degradation |
| Logging | Enable slow query log (threshold 1s) | Performance monitoring and debugging |
| TLS | Enforce SSL connections | Encryption in transit |
| Authentication | scram-sha-256 | Strongest PostgreSQL auth method |
| Port binding | Bind to 127.0.0.1 only | Internal Docker network only |

**pgbouncer integration:**

```yaml
# roles/postgresql/templates/pgbouncer.ini.j2
[databases]
{% for db in postgres_databases %}
{{ db.name }} = host=127.0.0.1 port=5432 dbname={{ db.name }}
{% endfor %}

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = {{ pgbouncer_max_client_conn | default(500) }}
default_pool_size = {{ pgbouncer_default_pool_size | default(25) }}
max_db_connections = {{ pgbouncer_max_db_connections | default(50) }}
min_stable_connections = 5
stats_period = 60

# TLS
ssl_cert = /etc/ssl/certs/pgbouncer.pem
ssl_key = /etc/ssl/private/pgbouncer.key

# Logging
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
```

### 3.2 Redis

**Ansible Role: `roles/redis`**

```yaml
# roles/redis/defaults/main.yml
---
redis_version: "7.2"
redis_port: 6379
redis_bind: "127.0.0.1"
redis_requirepass: "{{ vault_redis_password }}"
redis_maxmemory: "1gb"
redis_maxmemory_policy: "allkeys-lru"
redis_maxmemory_samples: 5
redis_appendonly: "yes"
redis_appendfsync: "everysec"
redis_save_enabled: true
redis_save_intervals:
  - seconds: 900
    changes: 1
  - seconds: 300
    changes: 10
  - seconds: 60
    changes: 1000
redis_rename_commands:
  FLUSHDB: ""
  FLUSHALL: ""
  CONFIG: ""
  DEBUG: ""
redis_tcp_keepalive: 60
redis_timeout: 300
redis_logfile: /var/log/redis/redis-server.log
```

**Key configuration practices:**

| Aspect | Best Practice | Rationale |
|--------|--------------|-----------|
| Bind address | 127.0.0.1 only | Never expose Redis publicly |
| Password | Always require authentication | Disable with `requirepass` |
| Max memory | Set explicit limit | Prevent OOM kills |
| Eviction policy | `allkeys-lru` or `volatile-lru` depending on use | Automatic cleanup |
| Persistence | `appendonly yes` + RDB snapshots | Crash recovery |
| Rename dangerous commands | FLUSHDB, FLUSHALL, CONFIG | Defense in depth |
| Client timeout | 300 seconds | Clean up idle connections |
| TCP keepalive | 60 seconds | Detect dead peers |
| Slow log | Enable with threshold | Performance monitoring |

### 3.3 MinIO

**Ansible Role: `roles/minio`**

```yaml
# roles/minio/defaults/main.yml
---
minio_version: "2024"
minio_root_user: "{{ vault_minio_root_user }}"
minio_root_password: "{{ vault_minio_root_password }}"
minio_console_port: 9001
minio_api_port: 9000
minio_console_address: ":9001"
minio_volumes: "/data/minio"
minio_browser: "enable"
minio_docs: "enable"
minio_region: "us-east-1"
minio_domain: "minio.{{ domain | default('example.com') }}"
minio_erasure_healing: true
minio_erasure_auto_healing: true
minio_rate_limit: true
minio_bucket_notification: false
minio_pprof_address: "localhost:7070"
```

**Key configuration practices:**

| Aspect | Best Practice | Rationale |
|--------|--------------|-----------|
| Erasure coding | Enable auto-healing | Data protection against disk failures |
| TLS | Always enable | Encrypt data in transit |
| Bucket policies | Set per-bucket policies | Least-privilege access |
| Versioning | Enable on critical buckets | Protection against accidental deletion |
| Lifecycle rules | Set expiry for temporary data | Cost management |
| Encryption | Enable SSE-S3 or SSE-KMS | Encrypt at rest |
| Monitoring | Enable metrics endpoint | Performance monitoring |
| Credentials | Store in secret vault | Never hardcode |

**MinIO bucket policies:**

```yaml
# roles/minio/files/bucket-policies/
# backup-bucket-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": ["*"]},
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": ["arn:aws:s3:::iacgenie-backups/*"]
    }
  ]
}

# cache-bucket-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": ["*"]},
      "Action": ["s3:ListBucket", "s3:GetObject", "s3:PutObject"],
      "Resource": [
        "arn:aws:s3:::iacgenie-cache",
        "arn:aws:s3:::iacgenie-cache/*"
      ]
    }
  ]
}
```

### 3.4 OpenBao

**Ansible Role: `roles/openbao`**

```yaml
# roles/openbao/defaults/main.yml
---
openbao_version: "1.16"
openbao_user: openbao
openbao_group: openbao
openbao_port: 8200
openbao_cluster_addr: "https://127.0.0.1:8200"
openbao_ui: true
openbao_listener_address: "127.0.0.1"
openbao_cluster_address: "127.0.0.1"
openbao_tls_enabled: true
openbao_tls_cert_file: /etc/openbao/tls/server.crt
openbao_tls_key_file: /etc/openbao/tls/server.key
openbao_tls_ca_cert_file: /etc/openbao/tls/ca.crt
openbao_storage_type: file
openbao_storage_dir: /opt/openbao/storage
openbao_audit_device_enabled: true
openbao_audit_file_path: /opt/openbao/audit/audit.log
openbao_initial_root_token: "{{ vault_openbao_root_token }}"
openbao_initial_keys: "{{ vault_openbao_initial_keys }}"
openbao_unseal_keys: "{{ vault_openbao_unseal_keys }}"
openbao_unseal_threshold: 3
openbao_unseal_total: 5
```

**Key configuration practices:**

| Aspect | Best Practice | Rationale |
|--------|--------------|-----------|
| Storage backend | Use file storage on same VM | Sufficient for single-VM setup |
| TLS | Always enable | Encrypt Vault communication |
| Audit logging | Enable file-based audit device | Compliance and forensics |
| Seal/Unseal | Shamir's threshold (3 of 5) | Security without HSM complexity |
| Auto-unseal | Consider Vault agent auto-unseal later | Eliminates manual unsealing |
| AppRoles | Use AppRole for service auth | Programmatic access without tokens |
| Secret engines | Enable only what's needed | Reduce attack surface |
| Token expiration | Set max TTL on all tokens | Prevent token accumulation |
| Backup | Regular snapshots of storage dir | Disaster recovery |

**OpenBao configuration template:**

```json
// roles/openbao/templates/openbao.hcl.j2
ui = {{ openbao_ui | default(true) | lower }}
listener "tcp" {
  address       = "{{ openbao_listener_address }}:{{ openbao_port }}"
  tls_disable   = {{ openbao_tls_enabled | default(true) | ternary(0, 1) | int == 1 | ternary(0, 1) }}
  tls_cert_file = "{{ openbao_tls_cert_file }}"
  tls_key_file  = "{{ openbao_tls_key_file }}"
  tls_ca_cert_file = "{{ openbao_tls_ca_cert_file }}"
}

storage "{{ openbao_storage_type }}" {
  path = "{{ openbao_storage_dir }}"
}

audit_file_sink "file_audit" {
  file_path = "{{ openbao_audit_file_path }}"
}

seal "shamir" {
  {% if openbao_unseal_threshold is defined %}
  threshold     = {{ openbao_unseal_threshold }}
  {% endif %}
  {% if openbao_unseal_total is defined %}
  shares        = {{ openbao_unseal_total }}
  {% endif %}
}

seal_transit {
  mount_path = "transit/"
  token     = "{{ vault_openbao_transit_token | default('') }}"
  address   = "{{ vault_openbao_transit_address | default('https://127.0.0.1:8200') }}"
}

log_level = "info"
```

### 3.5 Keycloak

**Ansible Role: `roles/keycloak`**

```yaml
# roles/keycloak/defaults/main.yml
---
keycloak_version: "25.0"
keycloak_admin_user: "admin"
keycloak_admin_password: "{{ vault_keycloak_admin_password }}"
keycloak_db_vendor: postgres
keycloak_db_host: postgres
keycloak_db_port: 5432
keycloak_db_user: "{{ postgres_user }}"
keycloak_db_password: "{{ vault_keycloak_db_password }}"
keycloak_db_database: "keycloak"
keycloak_hostname: "{{ domain | default('example.com') }}"
keycloak_https_required: true
keycloak_proxy_headers: forwarded
keycloak_spi_smtp_host: "{{ vault_smtp_host | default('smtp.cloudflare.com') }}"
keycloak_spi_smtp_port: "587"
keycloak_spi_smtp_user: "{{ vault_smtp_user }}"
keycloak_spi_smtp_password: "{{ vault_smtp_password }}"
keycloak_spi_smtp_from: "noreply@{{ domain | default('example.com') }}"
keycloak_spi_smtp_tls: "true"
keycloak_realm_import_file: "iacgenie-realm.json"
keycloak_initial_realm: "iacgenie"
```

**Key configuration practices:**

| Aspect | Best Practice | Rationale |
|--------|--------------|-----------|
| DB backend | Use PostgreSQL (external) | Not the embedded H2 database |
| HTTPS | Always enforce HTTPS | Keycloak handles auth tokens |
| Proxy headers | Configure `forwarded` proxy | Behind Nginx reverse proxy |
| Realm import | Pre-configured JSON realm file | Consistent realm across deployments |
| LDAP integration | Use LDAP federation | Enterprise SSO integration |
| SSL/TLS | Use proper certificates | End-to-end encryption |
| Admin security | Enable admin auth methods | MFA for admin accounts |
| Session management | Set appropriate timeout values | Balance security vs UX |
| Backup | Export realm configs regularly | Recovery capability |

**Keycloak realm import:**

```yaml
# roles/keycloak/tasks/realm-import.yml
---
- name: Deploy Keycloak realm configuration
  ansible.builtin.copy:
    content: "{{ lookup('file', 'roles/keycloak/files/{{ keycloak_realm_import_file }}') }}"
    dest: /opt/keycloak/{{ keycloak_realm_import_file }}
    mode: "0644"

- name: Wait for Keycloak to be ready
  ansible.builtin.wait_for:
    port: 8080
    delay: 10
    timeout: 120

- name: Import realm into Keycloak
  ansible.builtin.uri:
    url: "http://localhost:8080/admin/realms/master/clients"
    method: POST
    user: "{{ keycloak_admin_user }}"
    password: "{{ keycloak_admin_password }}"
    body_format: json
    body:
      clientId: "realm-management"
      # Realm import via admin REST API
  register: keycloak_import
  until: keycloak_import.status == 201
  retries: 5
  delay: 30
```

### 3.6 Gitea

**Ansible Role: `roles/gitea`**

```yaml
# roles/gitea/defaults/main.yml
---
gitea_version: "1.22"
gitea_port: 3000
gitea_ssh_port: 2222
gitea_domain: "{{ domain | default('example.com') }}"
gitea_root_user: "admin"
gitea_root_password: "{{ vault_gitea_admin_password }}"
gitea_service_email: "git@{{ domain | default('example.com') }}"
gitea_offline_mode: true
gitea_repo_root: /data/gitea/git
gitea_app_dir: /data/gitea
gitea_lfs_root: /data/gitea/lfs
gitea_backup_dir: /data/gitea/backups
gitea_backup_schedule: "0 3 * * 0"
gitea_backup_retention: 4
```

**Key configuration practices:**

| Aspect | Best Practice | Rationale |
|--------|--------------|-----------|
| SSH | Run on separate port (2222) | Avoid conflicts with host SSH |
| SMTP | Configure via vault credentials | Email notifications |
| Backups | Scheduled automated backups | Disaster recovery |
| LFS | Enable LFS for large files | Git LFS support |
| SSH host keys | Generate and store securely | Git clone SSH access |
| Webhooks | Use signed webhooks | Security |
| 2FA | Require for admin accounts | Security |
| Service accounts | Use tokens for CI/CD | Automated access |

**Gitea backup script:**

```bash
#!/bin/bash
# scripts/backup-gitea.sh
set -euo pipefail

TIMESTAMP=$(date -u +"%Y%m%d-%H%M%S")
BACKUP_DIR="/data/gitea/backups"
RETENTION_DAYS=${1:-4}

# Create backup
docker exec iacgenie-gitea gitea dump -c /app/gitea/conf/app.ini \
  -m git,lfs,sql -t "${BACKUP_DIR}/gitea-dump-${TIMESTAMP}.zip"

# Clean old backups
find "${BACKUP_DIR}" -name "gitea-dump-*.zip" -mtime +${RETENTION_DAYS} -delete

echo "Backup created: gitea-dump-${TIMESTAMP}.zip"
```

### 3.7 Nginx

(Already covered in Section 2.8, but expanded below)

**Security headers checklist:**

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` | HSTS enforcement |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `SAMEORIGIN` | Prevent clickjacking |
| `X-XSS-Protection` | `1; mode=block` | XSS filter |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer info |
| `Content-Security-Policy` | Site-specific | Prevent XSS/injection |
| `Permissions-Policy` | Restrict features | Disable unused browser features |

**SSL/TLS hardening:**

| Setting | Value | Rationale |
|---------|-------|-----------|
| Protocol | TLSv1.2, TLSv1.3 | No TLSv1.0/1.1 |
| Cipher suite | ECDHE + AES-GCM | Forward secrecy, authenticated encryption |
| OCSP stapling | Enabled | Faster TLS handshake |
| DH parameters | 2048+ bits | Stronger key exchange |
| Session tickets | Disabled | Forward secrecy |
| Session cache | Shared, 10m | Performance optimization |

### 3.8 Cloudflare Tunnel

**Configuration management best practices:**

| Aspect | Best Practice | Rationale |
|--------|--------------|-----------|
| Tunnel ID | Store in Ansible Vault | Never expose publicly |
| Credentials | Store as JSON file | Cloudflare auto-regenerates |
| Logging | Enable verbose logging | Debugging connectivity |
| Auto-restart | systemd restart policy | Resilience to failures |
| Resource limits | Resource limits for process | Prevent runaway processes |
| Metrics | Enable metrics endpoint | Monitoring and alerting |
| Routes | Define per-path routing | Granular control |
| Update strategy | Pin to specific versions | Reproducibility |

### 3.9 Docker Compose

**Security and reliability best practices for all compose files:**

```yaml
# Common patterns for all service compose files
# docker-compose-generator/templates/common.yml.j2

# Always specify:
restart: unless-stopped                  # Auto-restart on failure
healthcheck:                             # Health monitoring
  test: ["CMD-SHELL", "<service-health-check>"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s
deploy:                                  # Resource management
  resources:
    limits:
      memory: <service-specific>
      cpus: <service-specific>
    reservations:
      memory: <minimum>
logging:                                 # Log management
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
security_opt:
  - no-new-privileges:true
read_only: true                          # Read-only filesystem where possible
tmpfs:                                   # Temporary writable dirs
  - /tmp
networks:                                # Network segmentation
  - iacgenie-net                         # Main services network
  - internal-net                         # DB/cache only (when applicable)
```

**Security_opt patterns:**

| Pattern | When to use | Effect |
|---------|-------------|--------|
| `no-new-privileges:true` | All containers | Prevent privilege escalation |
| `apparmor:docker-default` | Most containers | Mandatory access control |
| `seccomp:unconfined` | **Never** | Avoid — removes security profile |

**Resource limits by service:**

| Service | Memory Limit | CPU Limit | Reserved Memory |
|---------|-------------|-----------|-----------------|
| PostgreSQL | 2G | 2.0 | 512M |
| Redis | 512M | 1.0 | 128M |
| MinIO | 4G | 2.0 | 1G |
| OpenBao | 1G | 1.0 | 256M |
| Keycloak | 2G | 2.0 | 512M |
| Gitea | 1G | 1.0 | 256M |
| Nginx | 512M | 1.0 | 128M |
| cloudflared | 256M | 0.5 | 64M |

**Logging driver configuration:**

```yaml
# Always use json-file driver with rotation
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
    tag: "{{ service_name }}"

# Alternative for high-throughput services
# logging:
#   driver: syslog
#   options:
#     syslog-address: "tcp://localhost:514"
#     tag: "iacgenie/{{ service_name }}"
```

### 3.10 System Hardening

**Comprehensive system hardening checklist:**

```yaml
# roles/common/tasks/system-hardening.yml
---
- name: Configure SSH hardening
  ansible.builtin.lineinfile:
    path: /etc/ssh/sshd_config
    regexp: "{{ item.regexp }}"
    line: "{{ item.line }}"
    validate: "sshd -t -f %s"
  loop:
    - regexp: "^#?PermitRootLogin"
      line: "PermitRootLogin prohibit-password"
    - regexp: "^#?PasswordAuthentication"
      line: "PasswordAuthentication no"
    - regexp: "^#?PubkeyAuthentication"
      line: "PubkeyAuthentication yes"
    - regexp: "^#?MaxAuthTries"
      line: "MaxAuthTries 3"
    - regexp: "^#?X11Forwarding"
      line: "X11Forwarding no"
    - regexp: "^#?AllowTcpForwarding"
      line: "AllowTcpForwarding no"
    - regexp: "^#?ClientAliveInterval"
      line: "ClientAliveInterval 300"
    - regexp: "^#?ClientAliveCountMax"
      line: "ClientAliveCountMax 2"
  notify: restart sshd

- name: Configure UFW firewall
  ansible.builtin.template:
    src: ufw.rules.j2
    dest: /etc/ufw/user.rules
    mode: "0640"
  notify: restart ufw

- name: Install and configure fail2ban
  ansible.builtin.template:
    src: fail2ban.j2
    dest: /etc/fail2ban/jail.local
    mode: "0600"
  notify: restart fail2ban

- name: Configure log rotation
  ansible.builtin.template:
    src: logrotate.conf.j2
    dest: /etc/logrotate.d/iacgenie
    mode: "0644"

- name: Configure system monitoring
  ansible.builtin.template:
    src: node-exporter.service.j2
    dest: /etc/systemd/system/node-exporter.service
  notify: restart node-exporter
```

**fail2ban configuration:**

```ini
# roles/common/templates/fail2ban.j2
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
banaction = ufw
banaction_allports = ufw-allports
action = %(action_mwl)s

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200

[nginx-http-auth]
enabled = true
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 5

[nginx-badbots]
enabled = true
port = http,https
filter = nginx-badbots
logpath = /var/log/nginx/access.log
```

**Log rotation:**

```ini
# roles/common/templates/logrotate.conf.j2
/var/log/iacgenie/*.log {
    weekly
    rotate {{ logrotate_retention | default(8) }}
    compress
    delaycompress
    missingok
    notifempty
    create 640 root adm
    postrotate
        systemctl reload nginx > /dev/null 2>&1 || true
    endscript
}

/var/log/cloudflared/*.log {
    weekly
    rotate {{ logrotate_retention | default(8) }}
    compress
    delaycompress
    missingok
    notifempty
    create 640 {{ cloudflared_user }} adm
}
```

---

## 4. Recommended Project Structure for IacGenie

Combining all the above, here's the final recommended structure:

```
iacgenie-ansible/                          # Main infrastructure repository
│
├── ansible.cfg                            # Global Ansible configuration
├── inventory/
│   ├── hosts.ini                          # Static inventory
│   ├── group_vars/
│   │   ├── all.yml                        # Global variables
│   │   ├── databases.yml                  # DB group variables
│   │   ├── services.yml                   # Service group variables
│   │   └── secrets.yml                    # ** ENCRYPTED with vault **
│   └── host_vars/
│       └── iacgenie-server.yml            # Host-specific overrides
│
├── playbooks/
│   ├── site.yml                           # Master orchestration
│   ├── bootstrap.yml                      # Initial provisioning
│   ├── docker.yml                         # Docker setup only
│   ├── services.yml                       # Deploy all services
│   ├── validate.yml                       # Post-deploy validation
│   ├── backup.yml                         # Backup all services
│   ├── restore.yml                        # Restore from backup
│   ├── hardened.yml                       # Security hardening
│   └── release/
│       ├── v1.0.yml                       # Version-specific playbooks
│       └── v1.1.yml
│
├── roles/
│   ├── common/                            # System basics, hardening
│   │   ├── tasks/main.yml
│   │   ├── tasks/hardening.yml
│   │   ├── tasks/ssh.yml
│   │   ├── tasks/firewall.yml
│   │   ├── tasks/fail2ban.yml
│   │   ├── tasks/logrotate.yml
│   │   ├── tasks/users.yml
│   │   ├── tasks/cleanup.yml
│   │   ├── defaults/main.yml
│   │   ├── handlers/main.yml
│   │   ├── templates/sshd_config.j2
│   │   ├── templates/jail.local.j2
│   │   ├── templates/logrotate.conf.j2
│   │   ├── meta/main.yml
│   │   └── molecule/default/
│   │
│   ├── docker/                            # Docker + Docker Compose
│   │   ├── tasks/install.yml
│   │   ├── tasks/configure.yml
│   │   ├── tasks/users.yml
│   │   ├── defaults/main.yml
│   │   ├── handlers/main.yml
│   │   ├── templates/docker-daemon.json.j2
│   │   ├── meta/main.yml
│   │   └── molecule/default/
│   │
│   ├── docker-compose-generator/          # Generates compose files
│   │   ├── tasks/main.yml
│   │   ├── defaults/main.yml
│   │   ├── templates/postgres.yml.j2
│   │   ├── templates/redis.yml.j2
│   │   ├── templates/minio.yml.j2
│   │   ├── templates/openbao.yml.j2
│   │   ├── templates/keycloak.yml.j2
│   │   ├── templates/gitea.yml.j2
│   │   ├── templates/nginx.yml.j2
│   │   ├── templates/cloudflared.yml.j2
│   │   ├── templates/docker-compose.yml.j2
│   │   └── molecule/default/
│   │
│   ├── postgresql/                        # PostgreSQL
│   ├── redis/                             # Redis
│   ├── minio/                             # MinIO
│   ├── openbao/                           # OpenBao
│   ├── keycloak/                          # Keycloak
│   ├── gitea/                             # Gitea
│   ├── nginx/                             # Nginx (system, not Docker)
│   ├── cloudflare-tunnel/                 # cloudflared
│   └── monitoring/                        # Prometheus + Grafana
│
├── scripts/
│   ├── backup.sh                          # Service backup script
│   ├── restore.sh                         # Service restore script
│   ├── health-check.sh                    # Post-deploy validation
│   ├── drift-check.sh                     # Configuration drift detection
│   └── migrate-postgres.sh                # PostgreSQL migration script
│
├── .github/workflows/
│   ├── ci-lint.yml
│   ├── ci-molecule.yml
│   └── ci-deploy.yml
│
├── .ansible-lint
├── .pre-commit-config.yaml
├── requirements.txt
├── requirements.yml
├── Makefile
├── VERSION
├── CHANGELOG.md
└── README.md
```

---

## 5. CI/CD Pipeline Design

```yaml
# .github/workflows/ci-deploy.yml
name: Infrastructure Deploy
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Ansible
        run: pip install ansible-core ansible-lint

      - name: Install roles and collections
        run: |
          ansible-galaxy install -r requirements.yml
          ansible-galaxy collection install -r collections/requirements.yml

      - name: Run ansible-lint
        run: ansible-lint

      - name: Deploy to production
        run: |
          ansible-playbook playbooks/site.yml \
            -i inventory/hosts.ini \
            --vault-password-file <(echo "$ANSIBLE_VAULT_PASSWORD")
        env:
          ANSIBLE_VAULT_PASSWORD: ${{ secrets.ANSIBLE_VAULT_PASSWORD }}
        # SSH key mounted via GitHub Actions secrets
        ssh-key: ${{ secrets.DEPLOY_SSH_KEY }}
```

---

## 6. Summary and Recommendations

### Key Findings

**For IacGenie's specific architecture (single VM, 11+ Docker services):**

1. **Use Ansible as the primary IaC tool** — Docker Compose is sufficient for container lifecycle. Terraform adds complexity without benefit for a single-VM setup.

2. **Generate Docker Compose files with Ansible templates** — This is the critical pattern. Instead of maintaining static compose files, generate them from Jinja2 templates. This gives you:
   - Environment-specific configuration
   - Centralized variable management
   - Full idempotency
   - Git-versionable infrastructure

3. **Project structure matters more than tools** — The recommended structure (roles per service, playbook orchestration, inventory-driven variables) is more important than any specific tool choice.

4. **Secrets management is non-negotiable** — Ansible Vault for local secrets, HashiCorp Vault when scaling. Never commit credentials.

5. **Per-service roles** — Each of the 11 services gets its own Ansible role with:
   - Service-specific defaults
   - Configuration templates
   - Health check verification
   - Resource limits

6. **System hardening is a separate role** — SSH, UFW, fail2ban, log rotation. Run this first.

7. **CI/CD pipeline** — Even for single-VM, automate everything. ansible-lint on PR, Molecule testing, automated deployment on main branch merge.

### Implementation Priority

| Priority | Task | Estimated Effort |
|----------|------|-----------------|
| P0 | Create project structure & inventory | 2 hours |
| P0 | Build system hardening role | 4 hours |
| P0 | Build Docker installation role | 2 hours |
| P1 | Build docker-compose-generator role | 6 hours |
| P1 | Add service compose file templates | 10 hours |
| P1 | Set up Ansible Vault | 1 hour |
| P2 | Add nginx role with reverse proxy config | 4 hours |
| P2 | Add Cloudflare Tunnel role | 3 hours |
| P2 | Set up CI/CD pipeline | 4 hours |
| P3 | Add Ansible Lint + Molecule testing | 6 hours |
| P3 | Build backup/restore automation | 4 hours |
| P4 | Add monitoring role | 6 hours |

### Architecture Diagram

```
                        ┌─────────────────────────────┐
                        │     Cloudflare Tunnel         │
                        │  (external ingress/routing)   │
                        └──────────────┬──────────────┘
                                       │ HTTPS
                                       ▼
                        ┌─────────────────────────────┐
                        │         Nginx (system)        │
                        │  (reverse proxy, TLS, HR)    │
                        │  HEADERS, Rate Limiting      │
                        └────┬─────┬─────┬─────┬──────┘
                               │     │     │     │
                    ┌──────────┤  ┌──┤  ┌──┤  ┌──┤  ┌──────────┐
                    ▼          ▼  ▼  ▼  ▼  └──┤  └──┤  ▼        ▼
                  ┌──────┐ ┌──────┐ ┌──────┐  │  ┌──────┐ ┌──────┐
                  │Postgres│ │Redis │ │MinIO │ ...│ Keycloak│ │Gitea │
                  └──────┘ └──────┘ └──────┘     └──────┘ └──────┘
                         │
                  ┌──────────┐
                  │ OpenBao  │
                  │ (Vault)  │
                  └──────────┘

    All containers on shared Docker network
    Nginx on host ports 80/443
    cloudflared on host port 3000
    Ansible orchestrates everything
```

---

*End of report. Generated for IacGenie production infrastructure deployment.*
