# Docker Compose: restart vs up -d (Critical Debugging Pattern)

## The Bug

When you modify a `docker-compose.yml` file on the host, running
`docker compose restart <service>` **does NOT re-read the compose file**.
The container keeps using its OLD configuration (command, env vars,
volumes, ports, etc.). The container is simply stopped and started
again with the same definition.

**Consequence:** Debugging a config issue by editing compose then
running `restart` will silently fail — the container continues using
the old config.

## The Fix

After modifying `docker-compose.yml`, **always use `up -d`** to
recreate the container:

```bash
docker compose up -d openbao
```

Or force-recreate if volumes/labels are also changing:

```bash
docker compose up -d --force-recreate openbao
```

## Why This Matters for OpenBao

The OpenBao crash in Aug 2026 was caused by this exact pattern:

1. The HCL config file was fixed on the host
2. The compose command was fixed (path change)
3. Admin ran `docker compose restart openbao` — **container kept old command**
4. Container crashed again because the old command pointed to the wrong HCL path
5. Only `docker compose up -d` (recreate) picked up the new command

**Verification:** Always check what the container is actually running
after any config change:

```bash
# Show the actual command the container is using:
docker inspect <container> --format='{{.Config.Cmd}}'

# If it differs from the compose file, run up -d
```

## Testing Change Impact Without Recreating

To verify what `up -d` would change:

```bash
docker compose config --services | xargs -I{} docker compose diff {}
```

Or compare the compose file output with running state:

```bash
docker compose config | grep -A20 'openbao:'
docker inspect --format='{{.Config.Cmd}} {{.Config.Env}}' iacgenie_openbao
```
