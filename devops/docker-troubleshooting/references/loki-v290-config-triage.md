# Loki v2.9.0 Config Triage

## Problem Pattern

Loki v2.9.x containers enter a restart loop. Logs show `failed parsing config: config.yaml,config/config.yaml does not exist` or container crashes on startup with config-related errors.

## Root Cause

The Loki v2.9.0 config struct uses Go struct tags. Any field that doesn't match a tag is **silently ignored** — not rejected with an error. This means:
- Common field names from older Loki versions (v1.x) are silently dropped
- Config appears to be applied but has no effect
- The service starts with unexpected defaults or fails because critical fields are missing

## How to Find the Correct Config

**Extract defaults from the Docker image:**
```bash
docker create --name loki-extract grafana/loki:2.9.8 loki -config.file=/etc/loki/local-config.yaml
docker cp loki-extract:/etc/loki/local-config.yaml /tmp/loki-default.yaml
docker rm loki-extract
```

This gives you the EXACT config the image ships with — a guaranteed-to-work starting point.

## Field Mappings (v1.x → v2.9.0)

| Old (v1.x) Field | Status in v2.9.0 | Notes |
|---|---|---|
| `storage.filesystem.directory` | ❌ DOES NOT EXIST | Silently ignored |
| `store_config.boltdb_shipper` | ❌ DEPRECATED | Removed in v2.x |
| `store_config.filesystem.directory` | ❌ DOES NOT EXIST | Silently ignored |
| `no_remove_wal` | ❌ DOES NOT EXIST | Silently ignored |
| `chunks_per_tail` | ❌ DOES NOT EXIST | Silently ignored |
| `storage.filesystem.directory` | ❌ DOES NOT EXIST | Use `common.storage.filesystem.chunks_directory` |
| `compactor.working_directory` | ✅ EXISTS | But must map to container volume, not host path |
| `logs_directory` | ❌ DOES NOT EXIST | Removed in v2.x |
| `retention_*` | ⚠️ PARTIAL | Use `limits_config.retention_period` instead |
| `server_log_level` | ❌ DOES NOT EXIST | Use `log_level` at root level or remove |

## Correct Field Names for v2.9.0

```yaml
auth_enabled: false
server:
  http_listen_port: 3100
common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks    # ← NOT storage.filesystem.directory
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory                   # ← NOT remote/etcd for single instance
schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper            # ← NOT tsdb
      object_store: filesystem
      schema: v11                       # ← NOT v13
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

Host paths must map to the **container paths**, not host filesystem paths:

```yaml
volumes:
  - /host/path/loki/data:/loki/chunks    # ← The chunks_directory in config
  - /host/path/loki/rules:/loki/rules    # ← The rules_directory in config
```

**Pitfall:** If `chunks_directory` is `/loki/chunks` but the volume mount only provides `/loki/data`, the container cannot find the chunks directory.

## API Endpoints

- **Push logs:** `POST /loki/api/v1/push` (NOT `/api/v1/push`)
- **Query logs:** `GET /loki/api/v1/query?query={job="test"}`
- **Schema:** `GET /loki/api/v1/schema`
- **Ready/health:** `GET /ready` (returns "ready" on success)

## Full Working Config

See the full working config in the SKILL.md under "Other Services → Loki v2.9.0 Working Config".

## Session Origin

Fixed 2026-08-12 via multiple iterative config deployments. Root cause: all config fields tested against Go struct tags; only fields matching tags are accepted by the Loki v2.9.0 config parser.
