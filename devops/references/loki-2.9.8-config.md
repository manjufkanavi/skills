# Loki 2.9.0+ Configuration Field Reference

## IMPORTANT: Extract Config From Docker Image

**CRITICAL:** Loki v2.9.x config uses Go struct tags. Fields that don't match struct tags are **silently ignored** — not rejected. This means config appears to be applied but has no effect.

**Always extract the default config from the Docker image as your starting point:**
```bash
docker create --name loki-extract grafana/loki:2.9.8 loki -config.file=/etc/loki/local-config.yaml
docker cp loki-extract:/etc/loki/local-config.yaml /tmp/loki-default.yaml
docker rm loki-extract
```

This gives you the EXACT config the image ships with.

## Invalid / Deprecated Fields (Silently Ignored)

| Field | Why | What to Use Instead |
|---|---|---|
| `storage.filesystem.directory` | Does not exist in v2.9.0 struct | `common.storage.filesystem.chunks_directory` |
| `store_config.boltdb_shipper` | Deprecated, removed in v2.x | Use `schema_config.configs[].store: boltdb-shipper` |
| `store_config.filesystem.directory` | Does not exist | `common.storage.filesystem.chunks_directory` |
| `no_remove_wal` | Does not exist | N/A |
| `chunks_per_tail` | Does not exist | N/A |
| `logs_directory` | Removed in v2.x | N/A |
| `server_log_level` | Removed in v2.x | Use `log_level` at root level |
| `retention_delete_delay` in compactor | Invalid | Use `retention_period` in `limits_config` |

## Working Config Template (v2.9.0 from Docker image defaults)

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

limits_config:
  retention_period: 720h

ruler:
  alertmanager_url: http://localhost:9093

analytics:
  reporting_enabled: false
```

## Volume Mapping

Host paths must map to the **container paths** (not host filesystem paths):

```yaml
volumes:
  - /host/path/loki/data:/loki/chunks    # matches chunks_directory in config
  - /host/path/loki/rules:/loki/rules    # matches rules_directory in config
```

**Pitfall:** If `chunks_directory` is `/loki/chunks` but the volume mount only provides `/loki/data`, the container cannot find the chunks directory.

## API Endpoints

- **Push logs:** `POST /loki/api/v1/push` (NOT `/api/v1/push`)
- **Query:** `GET /loki/api/v1/query?query={job="test"}`
- **Ready/health:** `GET /ready` (returns "ready" on success)

## Related Skills

- `docker-troubleshooting` (category: devops) — See `references/loki-v290-config-triage.md` for detailed field mappings
- `docker-troubleshooting` (category: devops) — See `references/keycloak-260-db-connection-fix.md` for Keycloak 26.0 database connection fix
