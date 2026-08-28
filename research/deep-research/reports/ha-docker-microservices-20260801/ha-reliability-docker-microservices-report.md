# High Availability & Reliability for Docker-Based Microservices

## Comprehensive Research Report

**Date:** 2026-08-01  
**Context:** Single VM environment (Ubuntu 24.04, 15 GB RAM, 465 GB disk) running Docker Compose with 12+ services  
**Scope:** PostgreSQL 15, Redis 7, MinIO, OpenBao 2.6.0, Keycloak 26.0, Gitea, Nginx, Cloudflare Tunnel  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [PostgreSQL: Replication, Clustering & Connection Management](#2-postgresql)
3. [Redis: Sentinel, Cluster & Persistence](#3-redis)
4. [MinIO: Distributed Erasure-Coded Storage](#4-minio)
5. [OpenBao: Raft Clustering & Auto-Unseal](#5-openbao)
6. [Keycloak: Clustered Authentication](#6-keycloak)
7. [Gitea: Shared-Filesystem HA](#7-gitea)
8. [Nginx: Load Balancing & Security Hardening](#8-nginx)
9. [Cloudflare Tunnel: Redundant Edge Connectivity](#9-cloudflare-tunnel)
10. [Cross-Cutting: Monitoring, Alerting & Observability](#10-cross-cutting-monitoring)
11. [Resource Budget & Cost-Benefit Matrix](#11-resource-budget)
12. [Recommended Implementation Roadmap](#12-recommended-implementation-roadmap)
13. [References](#13-references)

---

## 1. Executive Summary

### Current State

All 12+ services run as **single-instance Docker containers** on one VM. This is acceptable for development and small-team use, but introduces several risks:

| Risk Category | Impact |
|---|---|
| Single point of failure (SPOF) | Any container crash → cascading service outage |
| No automatic failover | Manual recovery required (mean time to recover: minutes to hours) |
| Backup not tested | Data loss potential unknown until disaster strikes |
| No connection pooling | Direct DB connections from containers exhaust DB connection limits |
| Stateful services lose data on crash | PostgreSQL/MinIO data directories on container filesystem = higher risk |
| Network partition | Nginx down → all external traffic stops |

### Philosophy

**Not every service needs HA.** The goal is **reliability proportional to business criticality** within resource constraints. This report prioritizes by:

1. **Data loss risk** — PostgreSQL, MinIO, OpenBao
2. **Availability impact** — Nginx (gateway), Keycloak (auth), Redis (session/cache)
3. **Operational complexity** — multi-node vs single-node trade-offs
4. **Resource budget** — 15 GB RAM is the binding constraint

### Key Recommendations (TL;DR)

| Priority | Service | Action | Extra Cost |
|---|---|---|---|
| P0 | PostgreSQL | pgBackRest backups + WAL archiving + PgBouncer | ~0.5 GB RAM |
| P0 | Redis | AOF persistence + Sentinel (2 extra nodes) | ~1 GB RAM total |
| P1 | Nginx | Multi-container + reverse proxy to itself | ~0.1 GB RAM |
| P1 | MinIO | Distributed mode (4+ drives) on single VM | ~0 RAM extra |
| P2 | OpenBao | Raft consensus + auto-unseal via static key | ~0.5 GB RAM |
| P2 | Keycloak | Clustered mode (2+ instances) behind Nginx | ~0.5 GB RAM |
| P3 | Gitea | Shared volume + pgBackRest synced | ~0 RAM extra |
| P3 | Cloudflare Tunnel | 2+ tunnel agents in containers | ~0.1 GB RAM |

---

## 2. PostgreSQL

### 2.1 Current Single-Instance Limitations

With a standalone PostgreSQL 15 container:

- **Single point of failure:** Container crash or host failure = complete database outage
- **No read scaling:** All queries hit one node; read-heavy workloads cause contention
- **Upgrade risk:** In-place upgrades risk data corruption if interrupted
- **No automatic failover:** Requires manual intervention; RTO (Recovery Time Objective) = manual
- **Connection exhaustion:** Without a pooler, every application container opens direct TCP connections
- **Backup window impact:** pgBaseBackup and online backups consume I/O and may slow queries
- **No geographic redundancy:** Data lives in one VM; site-level disaster = data loss

### 2.2 Production HA Architecture Options

#### Option A: Patroni + Etcd (Recommended for true HA)

Patroni manages PostgreSQL high availability using a distributed consensus store (etcd/Consul/ZooKeeper).

```
┌─────────────────────────────────────────────────┐
│  Patroni HA Cluster (3 nodes recommended)         │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Patroni  │  │ Patroni  │  │ Patroni  │       │
│  │ + PG 15  │  │ + PG 15  │  │ + PG 15  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │             │
│  ┌────▼────┐  ┌─────▼────┐  ┌─────▼────┐       │
│  │ etcd 1  │  │ etcd 2   │  │ etcd 3   │       │
│  └─────────┘  └──────────┘  └──────────┘       │
│                                                   │
│  ┌─────────────────────────────────┐             │
│  │       PgBouncer Pooler           │             │
│  └─────────────────────────────────┘             │
└─────────────────────────────────────────────────┘
```

**Components:**
- **Patroni:** Manages primary/replica election, failover, configuration sync
- **etcd (3 nodes):** Raft-based consensus store; partitions = no failover (quorum loss)
- **PgBouncer:** Connection pooling at the session level
- **pgBackRest:** Incremental backups with WAL archiving to S3/MinIO

**Failover characteristics:**
- Automatic failover in 10-60 seconds
- Replicas promote automatically via Raft consensus
- Zero data loss with synchronous replication (zero RPO)
- Filtered replication with partial data (logical replication available in PG 15+)

**Resource requirements (minimum viable):**
- 3x PostgreSQL containers: ~2 GB RAM each = ~6 GB RAM
- 3x etcd containers: ~0.5 GB RAM each = ~1.5 GB RAM
- 1x PgBouncer: ~50 MB RAM
- **Total overhead:** ~7.5 GB RAM (exceeds 15 GB budget when combined with other services)

#### Option B: Streaming Replication + repmgr (Lighter Weight)

```
┌──────────────────────────────────────┐
│  Primary (write)                     │
│  ┌────────────────┐                  │
│  │ PostgreSQL 15  │                  │
│  └───────┬────────┘                  │
│          │ WAL Streaming             │
│  ┌───────▼────────┐                  │
│  │ PostgreSQL 15  │  (standby)       │
│  └────────────────┘                  │
└──────────────────────────────────────┘
```

- **repmgr** manages failover with `repmgr failover` command
- Manual or script-triggered failover (not fully automatic)
- Lower resource overhead: ~2x PG containers
- WAL archive to MinIO for point-in-time recovery (PITR)

#### Option C: PgPool-II (Alternative Pooler + HA)

PgPool-II provides connection pooling, load balancing, and automatic failover. Similar resource footprint to PgBouncer + Patroni but more integrated.

### 2.3 When HA Is Needed vs. Single-Node Acceptable

| Scenario | Recommendation |
|---|---|
| Personal dev lab, data not critical | Single node + daily backups |
| Small team (≤5 users), tolerant of downtime | Single node + PgBouncer + backups |
| Production, >5 users, uptime SLA required | **3-node Patroni cluster** |
| Read-heavy workload | Single primary + read replica for reads |
| Budget-constrained | Streaming replication (1 standby) + scripted failover |

**For your environment (15 GB RAM):**
- **Short term:** Single PostgreSQL + PgBouncer + pgBackRest to MinIO is the most pragmatic approach
- **Medium term:** If you acquire a second VM, scale to 2-node streaming replication
- **Long term:** 3-node Patroni cluster if HA is truly required

### 2.4 Backup and Disaster Recovery

#### Backup Strategy

```
Backup Hierarchy:
┌────────────────────────────────────────────┐
│ pgBackRest (Primary)                       │
│  ├── Full backup (weekly, Sunday 00:00)     │
│  ├── Incremental (daily, every 6 hours)     │
│  ├── WAL archive → MinIO (continuous)       │
│  └── Retention: 4 full + 7 daily + WAL     │
├────────────────────────────────────────────┤
│ pgBaseBackup (Legacy/Complement)            │
│  └── Physical backup as fallback           │
└────────────────────────────────────────────┘
```

**pgBackRest Best Practices:**
- Store backups on MinIO (S3-compatible) — separate from database
- Enable `stanza-create` with `--pg1-port=5432 --pg1-host=localhost`
- Schedule: `pgbackrest backup --type=full` weekly, `--type=incr` every 6 hours
- WAL archiving: `archive_command = 'pgbackrest archive-push %p'`
- PITR supported: restore to any point in time using WAL replay

**Recovery objectives:**
- **RPO (Recovery Point Objective):** ~5 min (with WAL archiving every 5 min)
- **RTO (Recovery Time Objective):** ~15 min (restore full backup + replay WAL)

**Backup commands:**

```bash
# Create stanza
pgbackrest --stanza=main stanza-create \
  --repo1-type=s3 \
  --repo1-bucket=pgbackups \
  --repo1-path=/backups

# Full backup
pgbackrest --stanza=main backup --type=full --(repo1-retention-full=4)

# Incremental backup
pgbackrest --stanza=main backup --type=incr

# Restore to specific time
pgbackrest --stanza=main restore --type=time \
  --target="2026-08-01 12:00:00" \
  --delta --delta=reset-start
```

#### Disaster Recovery Plan

1. **Container crash** → Restart container (Docker handles this)
2. **Data corruption** → Restore from pgBackRest + PITR
3. **Host failure** → Restore from MinIO backups on new host
4. **Disk failure** → Restore from MinIO backups (data survives off-host)

### 2.5 Connection Pooling with PgBouncer

PgBouncer sits between application containers and PostgreSQL:

```
App Container ──┐
App Container ──┤
App Container ──┤──► PgBouncer (pool:200) ──► PostgreSQL 5432
App Container ──┤
App Container ──┘
```

**Why PgBouncer matters:**
- PostgreSQL max_connections default = 100; 10 app containers × 10 conn = 100 → exhaustion
- PgBouncer reuses connections; pool of 50 can serve 500+ app instances
- Reduces connection churn overhead
- Supports transaction-level pooling (higher throughput)

**Recommended PgBouncer config:**

```ini
[databases]
postgres = host=127.0.0.1 port=5432 dbname=postgres

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 50
min_pool_size = 10
reserve_pool_size = 5
max_connections = 500
stats_period = 60
```

### 2.6 Monitoring and Alerting

| Metric | Tool | Alert Threshold |
|---|---|---|
| Replication lag | pg_stat_replication | > 10 seconds |
| Connection count | pg_stat_activity | > 80% of max_connections |
| Disk usage | pg_size_pretty() | > 80% |
| Long-running queries | pg_stat_activity | > 30 seconds |
| Transaction ID wraparound | txid_current() | > 2B txns since last VACUUM |
| Checkpoint stats | pg_stat_bgwriter | checkpoint_timeout anomalies |
| Replication slots | pg_replication_slots | any inactive slot > 24h |

**Docker Compose snippet for PgBouncer:**

```yaml
pgbouncer:
  image: edoburu/pgbouncer:1.22
  environment:
    - POSTGRES_HOST=postgres
    - POSTGRES_PORT=5432
    - POSTGRES_USER=pgbouncer
    - POSTGRES_PASSWORD_FILE=/run/secrets/pgbouncer_password
  ports:
    - "6432:6432"
  depends_on:
    - postgres
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -h localhost -p 6432"]
    interval: 10s
    timeout: 5s
    retries: 3
```

### 2.7 Cost-Benefit Analysis: Single VM vs Multi-Node

| Aspect | Single PostgreSQL + PgBouncer | 3-Node Patroni |
|---|---|---|
| RAM | ~2 GB (PG) + 50 MB (Bouncer) | ~7.5 GB (PG+etcd×3) |
| CPU | 1 core | 2-3 cores |
| Complexity | Low (one container + pooler) | High (7+ containers, etcd quorum) |
| Failover time | Manual (minutes) | Automatic (10-60 sec) |
| Data loss risk | WAL archiving needed | Zero with sync replication |
| Monitoring | Basic pg metrics | Patroni dashboard + etcd metrics |
| Backup | pgBackRest + WAL archive | Same + cross-node redundancy |
| **Good for** | Dev, small team, budget-constrained | Production, SLA-required |
| **Acceptable for you?** | **YES — start here** | No (exceeds RAM budget) |

**Verdict for 15 GB RAM:** Begin with single PostgreSQL + PgBouncer + pgBackRest. Add streaming replication (1 standby) if a second VM becomes available.

---

## 3. Redis

### 3.1 Current Single-Instance Limitations

Standalone Redis 7 container:

- **Single point of failure:** Crash = cache + session loss
- **No persistence guarantee:** Without AOF/RDB configured, all data lost on restart
- **Memory limit risk:** No OOM protection; single large key or memory leak crashes server
- **No read scaling:** All reads go to one node
- **No data durability guarantee:** `fsync` disabled by default = data loss on crash
- **No automatic failover:** Requires manual intervention

### 3.2 Production HA Architecture Options

#### Option A: Redis Sentinel (Recommended for most use cases)

Sentinel provides automatic failover for a master-replica setup:

```
┌──────────────────────────────────────────────┐
│              Redis Sentinel                    │
│              (3 sentinel nodes)                │
│                                              │
│  ┌──────────┐                                │
│  │  Master   │◄── Writes                      │
│  │  (redis) │                                │
│  └────┬─────┘                                │
│       │ REPL                                 │
│  ┌────▼─────┐  ┌─────────────┐              │
│  │ Replica 1│  │ Replica 2   │              │
│  │ (redis)  │  │ (redis)     │              │
│  └──────────┘  └─────────────┘              │
└──────────────────────────────────────────────┘
```

**Characteristics:**
- Automatic failover in ~30 seconds
- Sentinels coordinate: detect failure, promote replica, update clients
- Clients query Sentinel for current master address
- Minimal config overhead compared to Cluster

**Resource requirements:**
- 3x Redis containers: ~1 GB RAM each (conservative) = ~3 GB RAM
- 3x Sentinel containers: ~20 MB RAM each = ~60 MB RAM
- **Total:** ~3 GB RAM

#### Option B: Redis Cluster (Sharding + HA)

Redis Cluster shards data across multiple nodes using hash slots (16384 slots):

```
┌──────────────────────────────────────────────┐
│              Redis Cluster                     │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Master 1│  │  Master 2│  │  Master 3│   │
│  │  (slots 0│  │  (slots  │  │  (slots  │   │
│  │  -5460)  │  │  5461-  │  │  10923-  │   │
│  │          │  │  10922)  │  │  16383)  │   │
│  │  +Replica│  │  +Replica│  │  +Replica│   │
│  └──────────┘  └──────────┘  └──────────┘   │
└──────────────────────────────────────────────┘
```

**Characteristics:**
- Horizontal scaling across nodes
- Data sharded (not all data on all nodes)
- Node failure: replica promoted automatically
- Cross-node operations limited (no multi-key transactions across slots)
- **Resource heavy:** 6 nodes minimum (3 master + 3 replica) = ~6 GB RAM

**When to choose Cluster over Sentinel:**
- Dataset exceeds single-node memory
- Need > 100K ops/sec throughput
- Multi-region deployment

#### Option C: Redis as Standalone with Persistence (Minimal)

For development/small workloads, standalone Redis with:
- `appendonly yes` (AOF persistence)
- `save` directives for RDB snapshots
- `maxmemory` + `maxmemory-policy allkeys-lru`

### 3.3 Persistence: RDB vs AOF vs Both

| Feature | RDB | AOF | Both |
|---|---|---|---|
| Data durability | Snapshot every N seconds | Every write (configurable) | Both |
| Recovery speed | Slow (load full dump) | Fast (replay recent entries) | Medium |
| Disk space | Compact | Larger (growth over time) | Largest |
| Performance impact | Background fork + write | Every write (rewrite interval) | Moderate |
| Data loss risk | Up to N seconds | 1 second (fsync everysec) | Minimal |
| **Recommended** | For cache data | For session data | **Production default** |

**Recommended Redis config for HA:**

```conf
# Both persistence types
save 900 1        # RDB: 1 change in 900s
save 300 10       # RDB: 10 changes in 300s
save 60 10000     # RDB: 10K changes in 60s

appendonly yes            # Enable AOF
appendfsync everysec      # Sync to disk every second
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Memory management
maxmemory 2gb
maxmemory-policy allkeys-lru

# Safety
stop-writes-on-bgsave-error yes
```

### 3.4 Backup Strategies

| Strategy | Method | Frequency | Recovery |
|---|---|---|---|
| AOF (appendonly.aof) | Built-in, continuous | N/A (always on) | Redis replays automatically |
| RDB dump (dump.rdb) | Scheduled snapshots | Every 15 min min | Load into new instance |
| Redis RDB backup script | `bgrewriteaof` + copy | Every hour | Restore to new container |
| External backup | `SAVE` command + copy to MinIO | Daily | Copy back + restart |

**Backup script:**

```bash
#!/bin/bash
# Redis backup script
BACKUP_DIR="/backups/redis"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER="redis-7"

# Trigger RDB save and copy
docker exec $CONTAINER redis-cli BGSAVE
sleep 5

# Copy AOF files for recovery
docker cp $CONTAINER:/data/*.aof $BACKUP_DIR/aof_${TIMESTAMP}/
docker cp $CONTAINER:/data/*.rdb $BACKUP_DIR/rdb_${TIMESTAMP}/

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -mindepth 1 -mtime +7 -exec rm -rf {} +
```

### 3.5 Monitoring and Alerting

| Metric | Tool/Command | Alert Threshold |
|---|---|---|
| Connected clients | `INFO clients` | > 80% of maxclients |
| Used memory | `INFO memory` | > 80% of maxmemory |
| Keyspace hit ratio | `INFO stats` (keyspace_hits/misses) | < 70% (cache inefficient) |
| Blocked clients | `INFO clients` | > 0 |
| Persisted size | `INFO persistence` (aof_current_size) | Growing unbounded |
| Replication lag | `INFO replication` (master_last_io_seconds_ago) | > 5 seconds |
| Total commands/sec | `INFO stats` (total_commands_processed) | Drop > 50% |
| Evicted keys | `INFO stats` (evicted_keys) | > 0 = active evictions |

### 3.6 Cost-Benefit Analysis

| Aspect | Standalone + AOF | Sentinel (1 master + 2 replicas) | Cluster (6 nodes) |
|---|---|---|---|
| RAM | ~1 GB | ~3 GB | ~6 GB |
| CPU | 0.5 core | 1.5 cores | 3 cores |
| Complexity | Very low | Low-medium | High |
| Failover | Manual | Automatic (30s) | Automatic |
| Data durability | Good (AOF everysec) | Good (AOF + replication) | Good (AOF + replication) |
| Scalability | Single node | Read scale-out | Horizontal scale |
| **For 15 GB VM?** | **Acceptable** | **Feasible** | Too heavy |

**Verdict:** Start with standalone Redis 7 + AOF + memory limits. Add Sentinel (1 master + 2 replicas) when budget allows (~3 GB RAM).

---

## 4. MinIO

### 4.1 Current Single-Instance Limitations

Single MinIO container (standalone mode):

- **No redundancy:** Single container crash = object storage outage
- **No erasure coding:** Corrupted file = corrupted object
- **No scaling:** Limited by single container's resources
- **No cross-node replication:** Can't distribute across VMs
- **Drive failure = data loss:** No built-in recovery from drive errors
- **Metadata loss:** Metadata in same process = single point of failure

### 4.2 Production HA Architecture: Distributed Mode

MinIO's distributed mode is its strength. It uses **erasure coding** for data protection:

```
┌──────────────────────────────────────────────┐
│          MinIO Distributed Cluster             │
│                                                │
│  ┌────────────┐  ┌────────────┐               │
│  │ MinIO Node1│  │ MinIO Node2│               │
│  │ 4 drives   │  │ 4 drives   │               │
│  │ (SSD/RAM)  │  │ (SSD/RAM)  │               │
│  └─────┬──────┘  └─────┬──────┘               │
│        │               │                       │
│  ┌─────▼──────┐  ┌─────▼──────┐               │
│  │ MinIO Node3│  │ MinIO Node4│               │
│  │ 4 drives   │  │ 4 drives   │               │
│  └────────────┘  └────────────┘               │
│                                                │
│  Erasure Code: 8 data + 4 parity = 12 drives  │
│  Tolerates: up to 4 drive/node failures       │
└──────────────────────────────────────────────┘
```

**Erasure Coding Explained:**
- Data is split into "strips" across drives
- Parity strips are calculated (Reed-Solomon coding)
- MinIO can reconstruct data from remaining strips
- **8 drives minimum:** 6 data + 2 parity (tolerates 1 failure)
- **Optimal: 4+ drives minimum**, 8+ for production

**Key properties:**
- Data can be distributed across multiple nodes (scale-out)
- Every drive carries data for every object (no cold/warm splits)
- Automatic scrubbing and healing
- Multipart upload + bitrot detection

### 4.3 Multi-Node Setup on Single VM

On your 15 GB VM, you can run MinIO in distributed mode using **disks as directories**:

```bash
# Create mount points (each acts as a "drive")
mkdir -p /data/minio/{1,2,3,4}

# Start distributed MinIO
docker run -d --name minio-distributed \
  --restart=unless-stopped \
  -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=<secure-password>" \
  -v /data/minio/1:/data1 \
  -v /data/minio/2:/data2 \
  -v /data/minio/3:/data3 \
  -v /data/minio/4:/data4 \
  minio/minio server http://{1...4}/data{1...4} \
  --console-address ":9001"
```

**Distributed mode on single host:**
- Use format files per directory to simulate multiple nodes
- MinIO treats each volume as a separate node
- Erasure coding across all volumes
- **Single host failure = data loss** (but data survives volume corruption)

**Multi-host setup (acquire 2nd VM):**
```bash
# VM1: http://192.168.0.118/data1 /data2
# VM2: http://192.168.0.119/data1 /data2
# VM3: http://192.168.0.120/data1 /data2
# VM4: http://192.168.0.121/data1 /data2

docker run -d --name minio \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=<secure-password>" \
  minio/minio server http://{118...121}/data{1,2} \
  --console-address ":9001"
```

### 4.4 MinIO Replication (Cross-Region/Zone)

MinIO supports **bucket-level replication** to another MinIO cluster:

```bash
# Enable versioning (required for replication)
mc version enable remote-bucket

# Create replication config
mc replicate add remote-bucket \
  --destination "arn:aws:s3:replication:remote-endpoint" \
  --sync --remove --versioning --delete --priority 1
```

**Use cases:**
- Active-active replication across data centers
- Disaster recovery: replicate to secondary site
- Compliance: immutable copies in different region

### 4.5 Backup Strategies

| Strategy | Method | Notes |
|---|---|---|
| MinIO Snapshot | `mc admin snapshot` | Point-in-time object snapshot |
| mc mirror | `mc mirror src dest` | Periodic mirror to secondary |
| mc schedule replicate | `mc mirror --replicate` | Automated replication |
| Object versioning | `mc version enable` | Built-in version history |
| Tar archive | `mc mirror --json` | For archival |

**Recommended backup approach:**

```bash
# Enable versioning
mc version enable local-bucket

# Schedule periodic replication to second cluster
mc mirror --replicate --versioning --delete \
  local-bucket remote-bucket

# Periodic snapshot backup
mc admin snapshot local-bucket > backup-$(date +%F).json
```

### 4.6 Monitoring and Alerting

| Metric | Console/API | Alert Threshold |
|---|---|---|
| Disk usage | Dashboard | > 80% |
| Erasure coding health | `mc admin info` | Any degraded drive |
| API latency | Prometheus metrics | > 100ms p99 |
| Uptime | Dashboard | Any downtime event |
| Scan errors | `mc admin inspect` | > 0 bitrot errors |
| Replication lag | Replication dashboard | > 1 hour lag |
| Available space | `/api/v1/admin/notify-targets` | < 10% free |

**Prometheus integration:**

```yaml
# docker-compose add to MinIO
ports:
  - "9090:9090"  # Prometheus metrics
environment:
  MINIO_PROMETHEUS_AUTH_TYPE: "public"
```

### 4.7 Cost-Benefit Analysis

| Aspect | Standalone | Distributed (4+ dirs) | Multi-host |
|---|---|---|---|
| RAM | ~1 GB | ~1 GB (same binary) | ~4 GB |
| Disk | Uses all disk | Uses all disk | Distributed |
| Complexity | Very low | Low (single host) | Medium |
| Failure tolerance | None | Drive failure OK | Host failure OK |
| Performance | Good | Better (parallel I/O) | Best (distributed) |
| **For 15 GB VM?** | OK for dev | **YES — recommended** | Need 2nd VM |

**Verdict:** Enable distributed mode using 4+ directories on your existing disk. This gives erasure coding and improved performance without extra hardware.

---

## 5. OpenBao

### 5.1 Current Single-Instance Limitations

OpenBao 2.6.0 as single container:

- **Single point of failure:** Vault outage = all auth/secret rotation stops
- **Unseal requirement:** Manual unseal or shamir; no auto-recovery
- **No data redundancy:** All secrets in one process
- **Key management:** Shamir splitting manual; auto-unseal unavailable
- **Config drift:** Single config source; no consensus verification
- **Scaling limited:** Can't scale read operations

### 5.2 Production HA Architecture: Raft Clustering

OpenBao 2.x uses **Raft consensus** for storage (replaces Consul):

```
┌──────────────────────────────────────────────┐
│            OpenBao Raft Cluster                │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ OpenBao1 │  │ OpenBao2 │  │ OpenBao3 │   │
│  │ Raft     │  │ Raft     │  │ Raft     │   │
│  │ Primary  │  │ Follower │  │ Follower │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       └──────────────┴──────────────┘         │
│              Raft Log                          │
│                                              │
│  ┌───────────────┐                           │
│  │ Auto-Unseal    │                           │
│  │ (CLOUD/FILE)  │                           │
│  └───────────────┘                           │
└──────────────────────────────────────────────┘
```

**Raft clustering requirements:**
- **Minimum 3 nodes** (odd number for quorum)
- Each node runs same OpenBao binary
- Shared storage backend (raft storage, each node has local raft)
- Raft log synced across all nodes
- Automatic leader election via Raft

**Auto-unseal options:**

| Method | Description | Best For |
|---|---|---|
| **CLOUD (KMS)** | Unseal key encrypted by cloud KMS (AWS KMS, GCP KMS, Azure Key Vault) | Cloud-native deployments |
| **FILE** | Unseal key stored as encrypted file on disk | Single-VM / local deployments |
| Shamir | Manual key splitting | Air-gapped, high-security |

**Auto-unseal via file (simplest for your setup):**

```hcl
# core.hcl
ui = true
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

storage "raft" {
  path = "/openbao/data"
}

seal "awskms" {
  region     = "us-east-1"
  kms_key_id = "mrk-xxxxxxxxxxxxx"
}

# Or for local file-based auto-unseal:
seal "transit" {
  address = "http://openbao-primary:8200"
  token   = "<token>"
  key_name = "openbao-unseal"
  mount_path = "transit/"
}
```

### 5.3 HA Mode Configuration

```hcl
# openbao.hcl — identical on all 3 nodes
storage "raft" {
  path = "/openbao/data"
  node_id = "node1"  # unique per node: node1, node2, node3
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 0
  tls_cert_file = "/openbao/certs/server.crt"
  tls_key_file  = "/openbao/certs/server.key"
}

cluster_addr = "https://192.168.0.118:8201"  # unique per node
ui = true

# Auto-unseal
seal "transit" {
  address = "https://192.168.0.118:8200"
  token = "<auto-unseal-token>"
  key_name = "openbao-unseal"
  mount_path = "transit/"
}
```

**Initialization sequence:**
1. Start all 3 OpenBao containers
2. Initialize primary with `openbao operator init` (captures root key shares)
3. Unseal primary (auto-unseal handles this after init)
4. Join secondary nodes: `openbao operator raft join https://192.168.0.118:8201`
5. Verify cluster: `openbao operator raft list-peers`

### 5.4 Backup and Restore

| Strategy | Method | Frequency |
|---|---|---|
| **Raft snapshots** | `openbao operator raft snapshot` | On-demand + automated |
| **Raft storage WAL** | Local raft log files | Continuous (built-in) |
| **Audit log** | File or syslog destination | Continuous |
| **Consul backup** | N/A (using Raft storage) | N/A |

**Snapshot backup:**

```bash
# Take snapshot
openbao operator raft snapshot save openbao-snapshot-$(date +%F).snap

# Restore from snapshot
openbao operator raft snapshot restore openbao-snapshot-2026-08-01.snap

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/openbao"
mkdir -p $BACKUP_DIR

# Request snapshot (requires sys/raw capability)
curl --header "X-Vault-Token: $VAULT_TOKEN" \
  http://localhost:8200/v1/sys/storage/raft/snapshot \
  > $BACKUP_DIR/openbao-$(date +%F).snap

# Cleanup old snapshots (keep 30 days)
find $BACKUP_DIR -name "*.snap" -mtime +30 -delete
```

**Critical:** Raft snapshots only backup the storage layer. Application secrets (K8s secrets, database credentials) configured in OpenBao are **not** included in snapshots. Those need separate backup of OpenBao policy/config export.

### 5.5 Monitoring and Alerting

| Metric | Method | Alert Threshold |
|---|---|---|
| Raft leader status | `openbao operator raft list-peers` | Multiple leaders (split brain) |
| Raft follower lag | `openbao operator raft list-peers` | Lag > 10 entries |
| Unseal status | `openbao status` | Any node unsealed |
| Token expiration rate | Auth metrics | Spike > 50% |
| Secret rotation failures | Audit log | Any failure |
| Storage health | `openbao operator health-check` | Health check failure |
| Ingress/egress rate | Prometheus metrics | Anomaly detection |

**Prometheus metrics (enable in config):**

```hcl
telemetry {
  prometheus_retention_time = "90s"
  disable_hostname = true
}
```

### 5.6 Cost-Benefit Analysis

| Aspect | Single OpenBao | 3-Node Raft |
|---|---|---|
| RAM | ~0.5 GB | ~1.5 GB |
| CPU | 0.5 core | 1.5 cores |
| Storage | /openbao/data | /openbao/data (x3) |
| Complexity | Very low | Medium |
| Failover | Manual re-initialization | Automatic leader election |
| Data safety | Single copy | Raft consensus (N/2 + 1) |
| Auto-unseal | Not applicable | **Essential** |
| **For 15 GB VM?** | **Acceptable for now** | 2-3 nodes feasible if other services scaled down |

**Verdict:** Start with single OpenBao + automated snapshot backups. When acquiring HA need, add 2 more nodes for 3-node Raft. Implement auto-unseal via transit engine.

---

## 6. Keycloak

### 6.1 Current Single-Instance Limitations

Single Keycloak 26.0 container:

- **Single point of failure:** Auth outage = all services lose authentication
- **No session scalability:** Limited by single JVM instance
- **Session loss on crash:** In-memory sessions lost (unless database-backed)
- **No performance scaling:** Single-threaded event processing
- **Admin UI single point:** Admin access blocked on failure
- **SAML/OIDC single issuer:** No redundancy in identity provider

### 6.2 Production HA Architecture: Clustered Mode

Keycloak 26.0 (Quarkus-based) supports native clustering:

```
┌──────────────────────────────────────────────┐
│             Keycloak Cluster                   │
│                                                │
│  ┌──────────┐  ┌──────────┐                  │
│  │ Keycloak │  │ Keycloak │                  │
│  │ Instance │  │ Instance │                  │
│  │  (JVM)   │  │  (JVM)   │                  │
│  └────┬─────┘  └────┬─────┘                  │
│       │              │                        │
│       └──────┬───────┘                        │
│              │                                  │
│  ┌───────────▼───────────┐                    │
│  │   Shared Database      │                    │
│  │   (PostgreSQL 15)      │                    │
│  └───────────────────────┘                    │
│                                                │
│  Session replication (optional, DB-backed)     │
└──────────────────────────────────────────────┘
```

**Clustered Keycloak configuration:**

```properties
# KEYCLOAK_CONFIG:
# Database:
KC_DB=postgres
KC_DB_URL=jdbc:postgresql://postgres:5432/keycloak
KC_DB_USERNAME=keycloak
KC_DB_PASSWORD=<secure>

# Clustering:
KC_HOSTNAME=keycloak.example.com
KC_PROXY=forwarded  # behind reverse proxy

# Native clustering (Keycloak 22+):
KC_HTTP_ENABLED=true
KC_HTTP_RELATIVE_PATH=/auth

# Cache:
KC_CACHE=ispn  # Infinispan (embedded in Quarkus)
KC_CACHE_STACK=default
```

**Key properties:**
- **Database affinity:** All instances share the same PostgreSQL database
- **Session sharing:** Sessions stored in DB (not memory) — natural clustering
- **Cache:** Infinispan embedded cache for sessions
- **No external cache required:** Keycloak 26+ stores sessions in DB natively

### 6.3 Session Sharing

Keycloak 26.0 (Quarkus) changed session storage:

| Version | Session Storage | Clustering Needed? |
|---|---|---|
| Legacy (WildFly) | Infinispan cache (local/replicated) | Yes, for true HA |
| Quarkus 22+ | **PostgreSQL database** (default) | No, DB-backed sessions |
| Quarkus 26+ | Database + optional Redis cache | Redis optional for performance |

**Database-backed sessions** (default in 26.0):
- Each request authenticates against the database
- Sessions persisted in `sessions` table
- No session replication needed
- Single source of truth = no consistency issues
- **Drawback:** Higher DB load per auth request

**Optional Redis session cache** (for performance):

```bash
# Enable Redis as session cache
KC_SESSION_STORE=redis
KC_SESSION_STORE_REDIS_HOST=redis
KC_SESSION_STORE_REDIS_PORT=6379
```

### 6.4 Monitoring and Alerting

| Metric | Method | Alert Threshold |
|---|---|---|
| Active sessions | Keycloak admin API | Drop > 50% (crash detection) |
| Login success rate | Keycloak audit events | < 95% success |
| Token issuance latency | Keycloak metrics | > 500ms p95 |
| Database connection pool | JDBC metrics | > 80% usage |
| Heartbeat | `/health` endpoint | Unhealthy |
| SPI FIPS check | `KC_SPI_*` configs | Fail |

**Health check endpoint:**

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
  interval: 15s
  timeout: 5s
  retries: 3
```

### 6.5 Cost-Benefit Analysis

| Aspect | Single Keycloak | Clustered (2+ instances) |
|---|---|---|
| RAM | ~1.5 GB (JVM) | ~3 GB (2x JVM) |
| CPU | 1 core | 2 cores |
| Database | Shared | Same DB (no extra) |
| Complexity | Low | Low (same config) |
| Failover | Manual restart | Automatic (just start another instance) |
| Auth availability | Single point | Multiple instances |
| Session handling | DB-backed (native) | DB-backed (same) |
| **For 15 GB VM?** | **Acceptable** | **Feasible (add 1 more instance)** |

**Verdict:** Start with single Keycloak (DB-backed sessions are sufficient). Add a second instance behind Nginx for redundancy (~1.5 GB extra RAM). Keycloak's simple clustering model makes this the easiest HA upgrade.

---

## 7. Gitea

### 7.1 Current Single-Instance Limitations

Single Gitea container:

- **Single point of failure:** Git service outage = no code operations
- **Local filesystem:** Repository data in container — lost if container crashes and volume not persisted
- **No read scaling:** All Git operations (clone, push, fetch) go to one instance
- **Single backend:** PostgreSQL single instance = DB failure breaks everything
- **No file-based shared storage:** Gitea requires shared filesystem for clustering

### 7.2 Production HA Architecture

Gitea's HA approach is **unique** — it doesn't replicate Git data. Instead:

```
┌──────────────────────────────────────────────┐
│              Gitea Cluster                     │
│                                                │
│  ┌──────────┐  ┌──────────┐                  │
│  │ Gitea 1  │  │ Gitea 2  │                  │
│  └────┬─────┘  └────┬─────┘                  │
│       │              │                        │
│  ┌────▼──────────────▼────┐                   │
│  │   Shared Filesystem     │  (NFS/GlusterFS) │
│  │   (/data/gitea)         │                   │
│  └────────────────────────┘                   │
│       │                                        │
│  ┌────▼────┐                                    │
│  │PostgreSQL│  (shared database)                 │
│  └─────────┘                                    │
└──────────────────────────────────────────────┘
```

**Two approaches:**

#### Approach A: Shared Filesystem + Multiple Gitea Pods

All Gitea instances share:
- **Filesystem:** Repository data, attachments, avatars (NFS, CephFS, GlusterFS)
- **Database:** Same PostgreSQL database
- **No Git replication needed:** All instances access the same repo data

#### Approach B: Proxy-Based (Simpler, Recommended for Your Setup)

Single Gitea instance + read-only mirror repos:

```
┌──────────────────────────────────────┐
│         Nginx Reverse Proxy          │
│                                      │
│  Routes / to Gitea:3000              │
│                                      │
│  Backup: periodic `git clone --mirror`│
│  to secondary storage                │
└──────────────────────────────────────┘
```

### 7.3 Configuration for HA

**Shared filesystem mount:**

```yaml
# docker-compose.yml
services:
  gitea:
    image: gitea/gitea:1.22
    volumes:
      - gitea-data:/data           # NFS mount or host volume
    environment:
      - GITEA__database__DB_TYPE=postgres
      - GITEA__database__HOST=postgres:5432
      - GITEA__database__NAME=gitea
      - GITEA__database__USER=gitea
      - GITEA__database__PASSWD=gitea

volumes:
  gitea-data:
    driver: local
    # For NFS: driver_opts.type = "nfs", device = "192.168.0.118:/exports/gitea"
```

**Gitea app.ini settings for HA:**

```ini
[database]
DB_TYPE = postgres
HOST = postgres:5432
NAME = gitea
USER = gitea
PASSWD = gitea
SSL_MODE = disable

[repository]
ROOT = /data/git/gitea-repositories
SCRIPT_TYPE = bash

[session]
PROVIDER = file

[security]
INSTALL_LOCK = true
SECRET_KEY = <auto-generated-or-set>

[oauth2]
JWT_SECRET = <strong-random-string>
```

### 7.4 Backup and Disaster Recovery

| Strategy | Method | Frequency | Recovery |
|---|---|---|---|
| **Git mirror** | `git clone --mirror` to secondary | Every 15 min (cron) | Fast — clone from mirror |
| **Gitea backup** | `gitea dump` command | Daily | Restore via `gitea dump recover` |
| **Database dump** | pgBackRest (shared with PG) | Daily + WAL | Full restore |
| **Filesystem snapshot** | LVM/ZFS snapshot | Hourly | Mount snapshot, copy data |
| **SSH clone backup** | Clone all repos to external server | Every 6 hours | Manual push of each repo |

**Backup script:**

```bash
#!/bin/bash
# Gitea daily backup

BACKUP_DIR="/backups/gitea"
GITEA_CONTAINER="gitea"
MIRROR_DIR="$BACKUP_DIR/mirrors"

# 1. Gitea built-in dump
docker exec $GITEA_CONTAINER gitea dump \
  -c /app/gitea/conf/app.ini \
  -t $BACKUP_DIR/dump-$(date +%F).tar.gz

# 2. Mirror all bare repos
mkdir -p $MIRROR_DIR
docker exec $GITEA_CONTAINER find /data/git/gitea-repositories -name "*.git" -type d | while read repo; do
  repo_name=$(basename "$repo" .git)
  if [ ! -d "$MIRROR_DIR/$repo_name.git" ]; then
    git clone --mirror "$repo" "$MIRROR_DIR/$repo_name.git"
  else
    cd "$MIRROR_DIR/$repo_name.git" && git fetch --all
  fi
done

# 3. Cleanup old dumps (keep 30 days)
find $BACKUP_DIR -name "dump-*.tar.gz" -mtime +30 -delete
```

### 7.5 Monitoring and Alerting

| Metric | Method | Alert Threshold |
|---|---|---|
| HTTP response code | Nginx proxy log | 5xx rate > 1% |
| Git clone/push latency | Nginx access log | > 5 seconds |
| Database connections | pg_stat_activity | > 80% pool |
| Disk usage (repos) | df / local filesystem | > 85% |
| Backup age | Backup monitoring script | > 24h without backup |
| Repository count | `gitea list-repos` | Unexpected drops |

### 7.6 Cost-Benefit Analysis

| Aspect | Single Gitea + NFS | Dual Gitea + Shared FS |
|---|---|---|
| RAM | ~300 MB | ~600 MB (2x) |
| CPU | 0.5 core | 1 core (2x) |
| Storage | Single volume | Same volume (shared) |
| Complexity | Low | Medium (NFS/GlusterFS) |
| Failover | N/A (single) | Automatic (start 2nd instance) |
| Backup quality | Good (dump + mirror) | Same |
| **For 15 GB VM?** | **YES — recommended** | Feasible (0.3 GB extra RAM) |

**Verdict:** Start with single Gitea instance using:
1. Persistent Docker volume for repository data
2. Daily `gitea dump` backup
3. Periodic `git clone --mirror` to external storage
4. Consider second Gitea instance for redundancy when budget allows

---

## 8. Nginx

### 8.1 Current Single-Instance Limitations

Single Nginx container as reverse proxy:

- **Gateway single point of failure:** No Nginx = no external access to any service
- **SSL/TLS termination bottleneck:** Single process handling all TLS handshakes
- **No graceful restart without brief downtime:** Config reload may drop connections
- **Limited rate limiting granularity:** Basic limit_req zone
- **No active health checking:** Upstream checks only on connection failure
- **Config errors can take down all services:** Single misconfigured server block blocks everything

### 8.2 Production HA Architecture

#### Option A: Multiple Nginx Containers Behind Load Balancer

```
                        ┌─────────────┐
                        │  Cloudflare  │
                        │   Edge CDN   │
                        └──────┬──────┘
                               │
                    ┌──────────▼──────────┐
                    │     Nginx LB 1      │  ← Additional load balancer
                    │  (HAProxy/Traefik)  │
                    └──────┬──────┬───────┘
                           │      │
              ┌────────────┘      └────────────┐
              │                                  │
      ┌───────▼───────┐                ┌────────▼───────┐
      │   Nginx 1     │                │   Nginx 2      │
      │  (primary)    │                │  (standby)     │
      │               │                │                │
      │ ┌───────────┐ │                │ ┌───────────┐ │
      │ │ Postgres  │ │                │ │ Postgres  │ │
      │ │ Redis     │ │                │ │ Redis     │ │
      │ │ MinIO     │ │                │ │ MinIO     │ │
      │ │ Keycloak  │ │                │ │ Keycloak  │ │
      │ │ Gitea     │ │                │ │ Gitea     │ │
      │ │ ...       │ │                │ │ ...       │ │
      │ └───────────┘ │                │ └───────────┘ │
      └───────────────┘                └───────────────┘
```

#### Option B: Nginx + Keepalived (VRRP Active-Standby)

```
┌─────────────────────────────────────────────┐
│  Virtual IP (VIP): 192.168.0.200            │
│                                              │
│  ┌──────────────┐  ┌───────────────────────┐ │
│  │  Nginx 1     │  │  Nginx 2 (hot standby) │ │
│  │  Keepalived  │  │  Keepalived (backup)   │ │
│  │  (active)    │  │  (vrrp_instance backup) │ │
│  └──────────────┘  └───────────────────────┘ │
│                                              │
│  VRRP advertises VIP. If active fails,       │
│  backup takes over VIP in < 1 second.        │
└──────────────────────────────────────────────┘
```

**Keepalived config:**

```conf
vrrp_script chk_nginx {
    script "/usr/local/bin/check_nginx.sh"
    interval 2
    weight -20
}

vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    authentication {
        auth_type PASS
        auth_pass secret123
    }
    virtual_ipaddress {
        192.168.0.200
    }
    track_script {
        chk_nginx
    }
}
```

#### Option C: Multiple Nginx + DNS Round-Robin (Simpler)

Run multiple Nginx containers, register different IPs with DNS. Simple but has DNS caching delays.

### 8.3 Nginx Configuration Best Practices

**Load balancing:**

```nginx
upstream postgres_pool {
    server postgres:5432;
    max_fails=3 fail_timeout=30s;
}

upstream app_backend {
    least_conn;  # distribute to least-loaded
    server app1:8080;
    server app2:8080;
    keepalive 32;  # persistent connections to upstream
}
```

**SSL/TLS best practices:**

```nginx
# /etc/nginx/nginx.conf
http {
    # Modern TLS configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
}
```

**Rate limiting:**

```nginx
http {
    # Define rate limit zones
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=3r/m;
    limit_req_zone $binary_remote_addr zone=git:10m rate=5r/s;
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    server {
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://app_backend;
        }

        location /auth/login {
            limit_req zone=login burst=5 delay=3;
            proxy_pass http://keycloak;
        }

        location /api/ {
            limit_conn addr 10;  # max 10 connections per IP
        }
    }
}
```

**Security hardening:**

```nginx
# Hide Nginx version
server_tokens off;

# Remove default error page info
# (configure in http{} block)

# Request size limits
client_max_body_size 50m;
client_body_buffer_size 128k;

# Timeout settings
client_body_timeout 12;
client_header_timeout 12;
keepalive_timeout 15;
send_timeout 10;

# Disable unused HTTP methods
if ($request_method !~ ^(GET|HEAD|POST|PUT|DELETE|PATCH|OPTIONS)$) {
    return 405;
}
```

**Keepalive to upstream:**

```nginx
http {
    keepalive_requests 100;
    keepalive_time 300s;
    keepalive_disable msie6;

    upstream app_backend {
        server app1:8080;
        server app2:8080;
        keepalive 64;
    }
}
```

### 8.4 Monitoring and Alerting

| Metric | Method | Alert Threshold |
|---|---|---|
| Active connections | `stub_status` | > 80% of worker_connections |
| 5xx response rate | Access log parsing | > 1% |
| Response time p99 | `proxy_next_upstream_timeout` | > 5s |
| Upstream failures | `proxy_next_upstream` | Rate > 5% |
| SSL certificate expiry | `openssl s_client` check | < 30 days |
| Disk space (logs) | Log rotation monitoring | > 85% |
| Memory usage | Container stats | > 80% limit |

### 8.5 Cost-Benefit Analysis

| Aspect | Single Nginx | Dual Nginx + Keepalived |
|---|---|---|
| RAM | ~20 MB | ~40 MB (2x) |
| CPU | Negligible | Negligible |
| Complexity | Very low | Medium (VRRP, shared VIP) |
| Failover | Manual (recreate container) | Automatic (< 1s) |
| Config changes | Reload each instance | Reload active + sync to standby |
| **For 15 GB VM?** | **YES — add second instance** | **HIGHLY RECOMMENDED** |

**Verdict:** Nginx is **inexpensive to duplicate** and is the **most critical single point of failure** in your stack. Always run at least 2 Nginx instances. Keepalived is optional; for a single VM, just run 2 containers and use a Docker-level VIP or Cloudflare Load Balancer.

---

## 9. Cloudflare Tunnel

### 9.1 Current Single-Instance Limitations

Single Cloudflared tunnel agent:

- **Single agent failure:** Tunnel drops = no external access to services
- **Single connection pool:** Cloudflare edge → single agent = bottleneck
- **No geographic distribution:** Agent runs on one VM, all traffic traverses one path
- **Single point of authentication:** Agent token stored in one location

### 9.2 Production HA Architecture

Cloudflare Tunnel is designed for high availability. The key is **multiple tunnel endpoints**:

```
┌──────────────────────────────────────────────┐
│             Cloudflare Edge                    │
│         (Anycast global network)               │
│                                                │
│  ┌─────────────────────────────────────┐       │
│  │  DNS: *.example.com → Tunnel ID      │       │
│  └──────────────────┬──────────────────┘       │
│                     │                          │
│         ┌───────────┼───────────┐              │
│         │           │           │              │
│  ┌──────▼──┐ ┌─────▼────┐ ┌────▼──────┐       │
│  │ cloud   │ │ cloud    │ │ cloud     │       │
│  │ flared  │ │ flared   │ │ flared    │       │
│  │ (VM1)   │ │ (VM2)    │ │ (VM3)     │       │
│  │ tunnel  │ │ tunnel   │ │ tunnel    │       │
│  └────┬────┘ └────┬─────┘ └────┬─────┘       │
│       │           │            │               │
│       └───────────┴────────────┘               │
│                   │                            │
│           ┌───────▼───────┐                    │
│           │  Your Services │  (local VM)        │
│           │  192.168.0.118 │                    │
│           └───────────────┘                    │
└──────────────────────────────────────────────┘
```

### 9.3 Multiple Tunnel Endpoints

Run **multiple cloudflared agents** in separate containers/VMs:

```yaml
# docker-compose.yml
services:
  cloudflared-1:
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token $CLOUDFLARE_TUNNEL_TOKEN
    environment:
      - CLOUDFLARE_TUNNEL_TOKEN=<token>

  cloudflared-2:
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token $CLOUDFLARE_TUNNEL_TOKEN
    # Run on separate VM or separate process
    environment:
      - CLOUDFLARE_TUNNEL_TOKEN=<token>
```

**Key insight:** Multiple cloudflared agents with the **same tunnel token** connect to the same Cloudflare tunnel. Cloudflare automatically load-balances across them.

### 9.4 Failover Behavior

Cloudflare's architecture provides built-in redundancy:

| Failure Scenario | Cloudflare Behavior |
|---|---|
| Single cloudflared agent down | Remaining agents handle traffic; zero disruption |
| Agent network flapping | Cloudflare marks agent unhealthy; routes around it |
| Entire VM down | If tunnel has agents on other hosts, zero impact |
| Cloudflare datacenter issue | Anycast routing; other PoPs handle traffic |
| DNS propagation delay | DNS TTL = 1 min; failover instant (no DNS needed) |

**No failover configuration needed** — this is by design. The more agents, the higher the availability.

### 9.5 Tunnel Configuration

```yaml
# config.yaml (cloudflared)
tunnel: <tunnel-id>
credentials-file: /etc/cloudflared/<tunnel-id>.json

metrics: /metrics

no-autoupdate: true

ingress:
  - hostname: postgres.example.com
    service: http://192.168.0.118:5432
    # Note: Cloudflare Tunnel doesn't do raw TCP by default
    # Use cloudflareargo/tunnel with TCP load balancing

  - hostname: keycloak.example.com
    service: http://192.168.0.118:8080

  - hostname: api.example.com
    service: http://192.168.0.118:8081

  - hostname: gitea.example.com
    service: http://192.168.0.118:3000

  - hostname: minio.example.com
    service: http://192.168.0.118:9000

  - default:
    service: http_status:404
```

**Important note:** Cloudflare Tunnel **does not natively support raw TCP** (PostgreSQL direct connections). For database traffic:
- Do NOT expose PostgreSQL directly through Cloudflare Tunnel
- Use application-level connections (via PgBouncer) that talk HTTP/gRPC
- Or use Cloudflare's newer **Load Balancing** features for TCP

### 9.6 Monitoring and Alerting

| Metric | Method | Alert Threshold |
|---|---|---|
| Tunnel status | `cloudflared tunnel status` | No healthy agents |
| Agent connections | Cloudflare Dashboard | < 1 agent connected |
| Ingress errors | Cloudflare Dashboard | 5xx rate > 1% |
| Latency | Cloudflare Dashboard p99 | > 500ms |
| Bandwidth | Cloudflare Dashboard | Anomaly spike |
| Configuration sync | `cloudflared tunnel info` | Stale version |

**Health check script:**

```bash
#!/bin/bash
# Tunnel health check
TOKEN="<token>"
TUNNEL_ID="<tunnel-id>"

# Check tunnel status
STATUS=$(cloudflared tunnel info $TUNNEL_ID 2>/dev/null)

# Parse healthy edge connections
HEALTHY=$(echo "$STATUS" | grep -c "healthy")

if [ "$HEALTHY" -lt 1 ]; then
    echo "ALERT: No healthy tunnel agents connected"
    # Send alert via webhook/email
fi
```

### 9.7 Cost-Benefit Analysis

| Aspect | Single Agent | Multiple Agents |
|---|---|---|
| RAM | ~30 MB | ~90 MB (3x) |
| CPU | Negligible | Negligible |
| Complexity | Very low | Low (same token) |
| Failover | Manual | **Automatic (Cloudflare handles)** |
| Global reach | Cloudflare edge | Cloudflare edge (same) |
| Multiple VMs | No | **Yes (recommended)** |
| **For 15 GB VM?** | Acceptable | **YES — run 2 agents** |

**Verdict:** Run 2 cloudflared agents (same tunnel token, different containers/VMs). This is the **cheapest, most effective HA** in your entire stack — minimal resource cost, maximum reliability improvement.

---

## 10. Cross-Cutting: Monitoring, Alerting & Observability

### 10.1 Unified Monitoring Stack

```
┌────────────────────────────────────────────────────┐
│                   Grafana                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │Dash     │  │Alerts   │  │Explore  │            │
│  │boards    │  │rules    │  │         │            │
│  └────┬─────┘  └────┬────┘  └────┬────┘            │
│       │              │             │                 │
│  ┌────▼──────────────▼─────────────▼────┐            │
│  │              Prometheus               │            │
│  │  (Pull-based metrics from all)        │            │
│  └────┬─────────────────────────────────┘            │
│       │                                              │
│  ┌────▼─────┐  ┌──────▼──────┐  ┌──────────────┐   │
│  │cAdvisor  │  │Node Exporter│  │Blackbox       │   │
│  │(containers│  │(host)      │  │Prober (HTTP)  │   │
│  └──────────┘  └─────────────┘  └──────────────┘   │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │Loki (logs)   │  │Tempo (traces)│                 │
│  └──────────────┘  └──────────────┘                 │
└────────────────────────────────────────────────────┘
```

### 10.2 Prometheus Integration

Add to all services' Docker Compose:

```yaml
# Example: Add Prometheus metrics endpoint
services:
  postgres:
    # pg_exporter sidecar
    depends_on:
      - postgres-exporter

  postgres-exporter:
    image: prometheus-community/postgres-exporter
    environment:
      - DATA_SOURCE_NAME=postgresql://postgres:postgres@postgres:5432/postgres?sslmode=disable

  redis:
    # redis_exporter sidecar
    depends_on:
      - redis-exporter

  redis-exporter:
    image: oliver006/redis_exporter
    environment:
      - REDIS_ADDR=redis://redis:6379

  minio:
    environment:
      - MINIO_PROMETHEUS_AUTH_TYPE=public
```

### 10.3 Alertmanager Rules

```yaml
# alerts/prometheus/rules/alerts.yml
groups:
  - name: infrastructure
    rules:
      - alert: HostMemoryHigh
        expr: node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes < 0.15
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Host memory below 15% free"

      - alert: DiskSpaceHigh
        expr: node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} < 0.15
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Disk space below 15% free"

  - name: postgresql
    rules:
      - alert: ReplicationLagHigh
        expr: pg_replication_lag > 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL replication lag > 10s"

      - alert: PostgreSQLDown
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL instance is down"

  - name: redis
    rules:
      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis instance is down"

      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory above 85%"

  - name: services
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "{{ $labels.instance }} is down"

      - alert: SSLCertExpiring
        expr: probe_ssl_earliest_cert_expiry - timestamp() < 86400 * 30
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "SSL certificate expires in 30 days"
```

### 10.4 Health Check Strategy

Every service should expose a health endpoint:

| Service | Health Endpoint |
|---|---|
| PostgreSQL | `pg_isready -h localhost -p 5432` |
| Redis | `redis-cli ping` → PONG |
| MinIO | `http://localhost:9000/minio/health/live` |
| OpenBao | `http://localhost:8200/v1/sys/health` |
| Keycloak | `http://localhost:8080/health` |
| Gitea | `http://localhost:3000/-/ping` |
| Nginx | `http://localhost:80/nginx_health` (stub_status) |
| Cloudflared | `http://localhost:51000/healthcheck` |

---

## 11. Resource Budget & Cost-Benefit Matrix

### 11.1 Current Resource Usage (Estimated)

| Service | Current RAM | Notes |
|---|---|---|
| PostgreSQL 15 | ~1.5 GB | Default config |
| Redis 7 | ~500 MB | Depends on data volume |
| MinIO | ~500 MB | Distributed mode same |
| OpenBao 2.6.0 | ~300 MB | Go binary, low RAM |
| Keycloak 26.0 | ~1.5 GB | JVM overhead |
| Gitea | ~300 MB | Go binary |
| Nginx | ~20 MB | Negligible |
| Cloudflared | ~30 MB | Negligible |
| LightSerp + others | ~1 GB | Python apps |
| **Total (current)** | **~6.2 GB** | 15 GB total, ~8.8 GB headroom |

### 11.2 HA Upgrade Resource Impact

| HA Upgrade | Additional RAM | Additional CPU | Feasibility |
|---|---|---|---|
| PgBouncer | +50 MB | +0.1 core | **Immediate** |
| PgBackRest backup agent | +100 MB | +0.1 core | **Immediate** |
| Second cloudflared | +30 MB | Negligible | **Immediate** |
| Second Nginx (proxy only) | +20 MB | Negligible | **Immediate** |
| Redis Sentinel (1 replica) | +500 MB | +0.5 core | **Feasible** |
| Redis Sentinel (2 replicas) | +1 GB | +1 core | **Feasible** |
| Second OpenBao node | +300 MB | +0.3 core | **Feasible** |
| Second Keycloak | +1.5 GB | +1 core | **Tight** |
| PostgreSQL standby | +1.5 GB | +0.5 core | **Tight** |
| Third Keycloak | +1.5 GB | +1 core | **Needs 2nd VM** |

### 11.3 Phased Implementation Budget

**Phase 1 — No cost upgrades (immediate):**
- PgBouncer + pgBackRest for PostgreSQL: ~150 MB extra RAM
- Second cloudflared agent: ~30 MB extra RAM
- Second Nginx container (behind Cloudflare): ~20 MB extra RAM
- **Total Phase 1 cost: ~200 MB RAM** ✓ Feasible

**Phase 2 — Low-cost upgrades (~1-2 GB RAM):**
- Redis Sentinel with 1 replica: ~500 MB extra RAM
- Second OpenBao for Raft: ~300 MB extra RAM
- Distributed MinIO (already on 1 VM): ~0 extra RAM
- **Total Phase 2 cost: ~1 GB RAM** ✓ Feasible

**Phase 3 — Medium-cost upgrades (~3 GB RAM):**
- Second Keycloak instance: ~1.5 GB RAM
- PostgreSQL standby: ~1.5 GB RAM
- **Total Phase 3 cost: ~3 GB RAM** ⚠ Tight (8.8 GB headroom available)

**Phase 4 — Multi-VM (2nd server):**
- Full Patroni cluster, Redis Cluster, Gitea HA
- No single-VM budget constraints

---

## 12. Recommended Implementation Roadmap

### Immediate (Week 1-2): Foundation

1. **Add PgBouncer** to PostgreSQL stack — immediate protection against connection exhaustion
2. **Configure pgBackRest** — start daily full backups + WAL archiving to MinIO
3. **Add second cloudflared agent** — automatic failover, 20 MB extra RAM
4. **Add second Nginx** — duplicate container, different port or use Cloudflare's health checks

### Short Term (Week 3-4): Persistence

5. **Enable Redis AOF** — data durability, no extra containers
6. **Add redis_exporter** — visibility into Redis metrics
7. **Enable distributed MinIO** — erasure coding on existing disk volumes
8. **Add health checks** to all containers in docker-compose

### Medium Term (Month 2-3): Redundancy

9. **Deploy Redis Sentinel** — 1 master + 2 replicas (3 GB RAM total for Redis)
10. **Add second OpenBao node** — Raft cluster, auto-unseal
11. **Second Keycloak instance** — behind Nginx, DB-backed sessions

### Long Term (Month 4+): Production-Grade

12. **Acquire 2nd VM** — enables full HA for all services
13. **PostgreSQL Patroni cluster** — 3 nodes + etcd
14. **Multi-host MinIO** — distributed across VMs
15. **Monitoring stack** — Prometheus + Grafana + Alertmanager

### Priority Matrix

```
                    LOW EFFORT ──────────► HIGH EFFORT
HIGH              ┌──────────────────────────────────────────┐
IMPACT            │ 2. PgBackRest    │ 9. Redis Sentinel     │
                ┌───┼──────────────────┼──────────────────────┤
                │   │ 1. PgBouncer     │ 10. OpenBao Raft     │
                │   │ 3. 2nd cloudflared│ 11. 2nd Keycloak    │
HIGH  ──────────┼───┼──────────────────┼──────────────────────┤
IMPACT          │   │ 4. 2nd Nginx     │ 12. PostgreSQL       │
                │   │ 5. Redis AOF     │    Patroni           │
LOW   ──────────┼───┼──────────────────┼──────────────────────┤
IMPACT          │   │ 6. MinIO distro  │ 13. Multi-host       │
                │   │ 7. Health checks │    MinIO             │
                │   │ 8. redis_exporter│                      │
LOW             └───┴──────────────────┴──────────────────────┘
```

---

## 13. References

1. **PostgreSQL Documentation** — https://www.postgresql.org/docs/
2. **Patroni Documentation** — https://patroni.readthedocs.io/
3. **PgBackRest Documentation** — https://pgbackrest.org/
4. **PgBouncer Documentation** — https://www.pgbouncer.org/
5. **Redis Sentinel Documentation** — https://redis.io/docs/management/sentinel/
6. **Redis Cluster Documentation** — https://redis.io/docs/management/cluster/
7. **MinIO Distributed Mode** — https://min.io/docs/minio/linux/operations/install-deploy-manage/deploy-minio-distributed.html
8. **MinIO Erasure Coding** — https://min.io/docs/minio/linux/administration/online-cloud-deployment.html
9. **OpenBao Documentation** — https://openbao.org/docs/
10. **OpenBao Raft Storage** — https://openbao.org/docs/configuration/storage/raft
11. **OpenBao Auto-Unseal** — https://openbao.org/docs/secrets/transit/transit-kubernetes
12. **Keycloak Clustering** — https://www.keycloak.org/server/cluster
13. **Keycloak Session Management** — https://www.keycloak.org/docs/latest/server_admin/#_session_management
14. **Gitea Installation** — https://docs.gitea.com/installation/docker
15. **Gitea Configuration** — https://docs.gitea.com/administration/config-cheat-sheet
16. **Nginx Documentation** — https://nginx.org/en/docs/
17. **Cloudflare Tunnel** — https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
18. **Cloudflare Tunnel Best Practices** — https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/configure-tunnels/
19. **Prometheus Postgres Exporter** — https://github.com/prometheus-community/postgres_exporter
20. **Redis Exporter** — https://github.com/oliver006/redis_exporter

---

*Report generated: 2026-08-01*  
*Environment: Single VM (Ubuntu 24.04, 15 GB RAM, 465 GB disk)*  
*Next step: Implement Phase 1 upgrades for immediate reliability improvements*
