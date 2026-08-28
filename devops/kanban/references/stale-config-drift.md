# Stale Deployed Config Drift

## Problem: Template Is Correct But Running Service Is Broken

The Ansible template (`.j2` file) has the correct configuration, but the deployed config on the VM is stale/wrong. The service crash-loops because it's reading the old config.

### Why This Happens

1. Template is updated in the repo but the deploy task was never re-run on the VM
2. Config was manually edited on the VM and is now out of sync with the template
3. The deploy task uses `lineinfile` or `copy` without `force: yes`, so it skips when the file already exists with same content hash
4. A previous deploy partially failed, leaving a mixed state

### Diagnosis

```bash
# Compare template (local) vs deployed config (remote)
ssh user@vm "cat /path/to/deployed/config"
# vs
cat roles/<role>/templates/config.yml.j2
```

If they differ, the deployed config is stale.

### Fix Pattern

```bash
# 1. Redeploy the template via ansible ad-hoc (bypasses playbook tag issues)
ansible <inventory> -m template \
  -a "src=roles/<role>/templates/config.yml.j2 \
      dest=/path/on/vm/config.yml \
      owner=<user> group=<group> mode=0644" \
  -i inventory

# 2. Restart the affected service
ssh user@vm "docker restart <container>"

# 3. Verify
ssh user@vm "docker inspect <container> --format '{{.State.Status}}'"
```

### Redis-Specific Case (Aug 2026)

- **Symptom**: `iacgenie_redis` in crash loop with `FATAL CONFIG FILE ERROR: No such file or directory` on line `dir /home/mkanavi/docker/iacgenie/data/redis`
- **Template** (`redis.conf.j2`): had correct `dir /data` (container-internal path)
- **Deployed config**: had stale `dir /home/mkanavi/docker/iacgenie/data/redis` (host path)
- **Root cause**: Template was fixed in a prior commit but the deploy task was never re-run; the old config file on the VM was skipped on subsequent runs because it "already existed"
- **Fix**: `ansible iacgenie-server -m template -a "src=roles/docker-compose-generator/templates/redis.conf.j2 dest=/home/mkanavi/docker/iacgenie/templates/redis.conf owner=mkanavi group=mkanavi mode=0644" -i inventory` then `docker restart iacgenie_redis`

### Prevention

1. **Always run full playbook after template changes** — even if tags seem to match, run `ansible-playbook site.yml -i inventory` to ensure all templates are deployed
2. **Add config diff to verification gates** — every infra task should diff the deployed config against the template
3. **Use `force: yes` in copy/template tasks** when the config must match the template exactly
4. **Check `docker logs` for FATAL CONFIG FILE ERROR** — this means the config references a path that doesn't exist inside the container, usually because the config has host paths instead of container-internal paths.
