# Compose Drift Detection - Multi-Architecture Comparison

## The Problem

Infrastructure projects often accumulate **multiple docker-compose files** over time:
- An **ansible template** (`docker-compose.yml.j2`) that generates one architecture
- A **hand-written compose** (`docker-compose-unified.yml`) that defines another
- Environment-specific files (`docker-compose-newvm.yml`, `docker-compose-iacgenie.yml`)

When multiple compose files target the **same data paths** (e.g., `/home/mkanavi/docker/iacgenie/`), they represent **competing definitions** of the same infrastructure. The ansible templates may describe the "intended" state while the hand-written file describes what's actually running.

## Drift Detection Procedure

### Step 1: Discover All Compose Files

```bash
# On the ansible repo
find infra/ -name "docker-compose*" -type f | sort

# On the VM
ssh user@vm 'find ~/docker -name "docker-compose*" | sort'

# Also check for .yaml extension
find . -name "docker-compose*.yaml" | sort
```

### Step 2: Compare Key Dimensions

For each compose file, extract comparable fields:

```bash
# Service count
grep -c '^  [a-z]' file1.yml file2.yml

# Network count and names
grep -E '^\s+name:|^\s+driver:' file*.yml

# Image versions (pinned vs :latest)
grep 'image:' file*.yml

# Port mappings
grep -E '^\s+- "127' file*.yml

# Volume mounts
grep -E '^\s+- /home' file*.yml

# Security settings
grep -E 'cap_drop|security_opt|no-new-privileges' file*.yml

# Resource limits
grep -E 'memory:|cpus:' file*.yml

# Health checks
grep -E 'healthcheck|test:' file*.yml
```

### Step 3: Build the Drift Matrix

Create a table comparing each service across architectures:

| Dimension | Ansible Template | Hand-Written Unified | Difference | Risk |
|-----------|-----------------|---------------------|------------|------|
| Networks | 3-tier | 1 flat | Isolation loss | High |
| Redis auth | .env file | --requirepass | Config inconsistency | Low |
| PostgreSQL user | lightsrp | postgres | Username mismatch | High |
| Keycloak command | start | start-dev | Dev mode enabled | High |
| OpenBao image | openbao/openbao | quay.io/openbao | Registry diff | Low |
| Resource limits | Memory only | Memory + CPU | No CPU throttling | Medium |
| Security | No cap_drop | cap_drop: ALL | Weak security | High |
| Logging | External | Built-in | Different stacks | Medium |

### Step 4: Identify Breaking Mismatches

Functional incompatibilities that could cause runtime failures:

1. **Username mismatches** - PostgreSQL `lightsrp` vs `postgres` means either the ansible template or the unified file has the wrong username
2. **Keycloak mode** - `start-dev` enables auto-user creation and removes production security hardening
3. **Port conflicts** - Services may listen on different ports in different compose files
4. **Service name resolution** - Ansible uses short names (`openbao:8200`), unified uses hyphenated names (`iacgenie-openbao:8200`)
5. **Network connectivity** - Services on different networks cannot communicate if one uses 3-tier and another uses flat

### Step 5: Determine the Source of Truth

Ask:
- When was the last ansible run? (`ssh user@vm 'stat ~/docker/iacgenie/docker-compose.yml'`)
- When was the last manual compose up? (`ssh user@vm 'stat ~/docker/iacgenie/docker-compose-unified.yml'`)
- Which file is actually referenced by the running compose project? (`ssh user@vm 'docker compose -p iacgenie ps'`)
- Does the ansible template match what's running? (`ansible-playbook --check`)

## Common Drift Patterns

### Pattern A: Evolution Without Migration
The hand-written file is newer and more secure, but ansible templates were not updated. The ansible scripts become **stale documentation** that no longer represents reality.

**Fix:** Backport hand-written improvements into ansible templates, or deprecate one.

### Pattern B: Dual Infrastructure
Both compose files are used simultaneously for different purposes. The ansible template is for new VMs, the hand-written file is for the existing VM.

**Risk:** New deployments differ from production. The two setups will diverge over time.

**Fix:** Choose one as canonical, remove the other, document the decision.

### Pattern C: Retrospective Ansible
The ansible templates were written AFTER the hand-written compose was deployed. They never ran on the target VM.

**Detection:** Check if ansible config files (`.vault_key`, `ansible.cfg`) exist on the VM. If not, ansible never ran.

**Fix:** Run ansible on a test VM first, or convert the hand-written compose to an ansible template.

## Recommendations

1. **Decide on one compose architecture** and remove duplicates. Document why.
2. **Keep ansible templates in sync** with whatever is actually deployed.
3. **Add a drift check task** to CI/CD: compare git head of ansible template against deployed compose on last known-good VM snapshot.
4. **Commit generated compose files** to git as golden reference. Any manual edits should be tracked.
5. **Use `docker compose config`** to validate compose files before deployment.
6. **Add network consistency checks** to pre-deploy validation.