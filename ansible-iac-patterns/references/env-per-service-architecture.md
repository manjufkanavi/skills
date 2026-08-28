# Per-Service `.env` Architecture

## Problem

When multiple Ansible service roles deploy to the same `.env` file, idempotency breaks:

1. Role A writes `.env` with its variables
2. Role B writes `.env` with its variables (overwrites A's)
3. Role C writes `.env` with its variables (overwrites A's and B's)
4. Next playbook run: Role A sees `.env` has different content → `changed=true`
5. Every role reports changed on every run → `changed=21` on every idempotency check

## Solution: Per-Service `.env` Files + Merge

### Step 1: Each role deploys to its own file

Change the template destination in each service role's `tasks/main.yml`:

```yaml
# Before (all roles)
- name: "PostgreSQL | Deploy environment file"
  ansible.builtin.template:
    src: .env.j2
    dest: /home/mkanavi/iacgenie-unified-infra/.env
    owner: mkanavi
    group: mkanavi
    mode: "0600"
  notify: Restart postgresql

# After (per-service)
- name: "PostgreSQL | Deploy environment file"
  ansible.builtin.template:
    src: .env.j2
    dest: /home/mkanavi/iacgenie-unified-infra/.env.postgres
    owner: mkanavi
    group: mkanavi
    mode: "0600"
  notify: Restart postgresql
```

### Step 2: Generator role merges `.env.*` into `.env`

Add a merge task in `docker-compose-generator/tasks/env-merge.yml`:

```yaml
- name: "Compose Gen | Merge .env.* files into unified .env"
  ansible.builtin.shell: |
    set -euo pipefail
    cd /home/mkanavi/iacgenie-unified-infra
    {
      echo "# Unified environment file"
      echo "# Managed by Ansible - DO NOT EDIT MANUALLY"
      echo "# Merged from individual service .env.<service> files"
      for f in .env.postgres .env.redis .env.minio .env.openbao .env.keycloak .env.gitea .env.lightserp .env.searxng .env.nsqd .env.pagezen; do
        if [ -f "$f" ]; then
          grep -v '^#' "$f" | grep -v '^$'
        fi
      done
    } > .env.new
    if ! diff -q .env.new .env > /dev/null 2>&1; then
      mv .env.new .env
      echo "MERGED"
    else
      rm -f .env.new
      echo "UNCHANGED"
    fi
  register: env_merged
  args:
    executable: /bin/bash
  notify: Reload docker compose
  changed_when: "'MERGED' in env_merged.stdout"
```

Key details:
- **`grep -v '^#'`** strips comment lines from each service's `.env.*` file
- **`diff -q`** compares merged output with existing `.env`
- **`echo "MERGED"` / `echo "UNCHANGED"`** makes `changed_when` report correctly
- **`changed_when`** uses the registered variable to determine if the file actually changed

### Step 3: Run generator AFTER service roles

In `playbooks/services.yml`, move `docker-compose-generator` to run last:

```yaml
roles:
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
  - role: docker-compose-generator   # ← LAST, after all services
  - role: nginx
  - role: cloudflare_tunnel
```

### Step 4: Include merge task in generator

In `docker-compose-generator/tasks/main.yml`:

```yaml
- name: "Compose Gen | Merge .env.* service files"
  ansible.builtin.import_tasks: env-merge.yml
```

## Result

- Each service role writes to a unique `.env.<service>` → idempotent per-service
- Generator merges at deploy time → unified `.env` for Docker Compose
- `changed=0` on idempotent runs (no spurious file changes)
- Docker Compose auto-loads `.env` from the compose file's directory

## Service name-to-file mapping

| Service | `.env` file |
|---------|-------------|
| PostgreSQL | `.env.postgres` |
| Redis | `.env.redis` |
| MinIO | `.env.minio` |
| OpenBao | `.env.openbao` |
| Keycloak | `.env.keycloak` |
| Gitea | `.env.gitea` |
| LightSerp | `.env.lightserp` |
| SearXNG | `.env.searxng` |
| NSQD | `.env.nsqd` |
| PageZen | `.env.pagezen` |
