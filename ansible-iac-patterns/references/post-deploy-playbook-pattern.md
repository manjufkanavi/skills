# Post-Deploy Playbook Pattern

Covers two patterns for tasks that must run AFTER all Docker containers are started.

## Pattern A: `import_tasks` in services.yml (Preferred — Unseal)

Use this for OpenBao unseal: add `import_tasks` in `services.yml` after the `roles:` section. Runs automatically, no separate playbook needed.

```yaml
# playbooks/services.yml
- hosts: iacgenie-server
  become: true

  roles:
    - ...all service roles...
    - docker-compose-generator  # LAST

  # Post-deploy: auto-run unseal after compose
  tasks:
    - import_tasks: roles/openbao/tasks/unseal.yml
      when: not openbao_skip_unseal | default(false) | bool
```

**Skip unseal:** Set `openbao_skip_unseal: true` in inventory/host_vars.

## Pattern B: Standalone Verification Playbook (Read-Only)

Use for manual verification without full redeploy. Health checks, readiness probes, container listing.

```yaml
# playbooks/post-deploy.yml
---
- hosts: iacgenie-server
  become: true
  tasks:
    # OpenBao read-only health
    - name: "OpenBao | Check container health"
      ansible.builtin.command: docker inspect --format='{{ .State.Health.Status }}' iacgenie_openbao
      register: openbao_health
      changed_when: false
      failed_when: false

    # Keycloak readiness
    - name: "Keycloak | Check admin UI"
      ansible.builtin.uri:
        url: "http://127.0.0.1:8083/health/ready"
        status_code: 200
      register: keycloak_health
      retries: 30
      delay: 10
      changed_when: false
      failed_when: false

    # All containers overview
    - name: "Docker | List containers"
      ansible.builtin.command: docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
      register: docker_ps
      changed_when: false
```

```bash
# Verify readiness without redeploy
ansible-playbook -i inventory/hosts.ini playbooks/post-deploy.yml
```

## Tasks That Belong in Pattern A (import_tasks)

| Task | Why import in services.yml? |
|------|-----------------------------|
| OpenBao auto-unseal | Must run after compose, before user can access the service |
| DB migration apply | Needs running database, part of deployment |

## Tasks That Belong in Pattern B (standalone)

| Task | Why standalone? |
|------|-----------------|
| Health checks | Read-only, verify after any deploy |
| Container listing | Diagnostic, not part of deployment |
| Service readiness probes | Manual verification, not deployment |

## Tasks That Belong Elsewhere

| Task | Where |
|------|-------|
| OpenBao init (first boot) | OpenBao role, before compose |
| Keycloak admin init | Separate script (needs admin UI) |
| MinIO bucket creation | Role or separate script |
| Gitea initial setup | Role (HTTP API, needs running service) |
| Seed OpenBao KV stores | Post-unseal, via script or API |
