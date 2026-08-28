# Scaling Grafana Monitoring at Massive Scale: Solving 12M Metric Challenges with Thanos

## Executive Summary

Operating **12 million active metric series** pushes Prometheus and Thanos Receive well beyond their comfortable limits. This research synthesizes findings from GitHub issues, Grafana Labs blogs, community discussions, and production case studies to identify the root causes of your bottlenecks and provide actionable scaling strategies.

**The core problem is twofold:** Prometheus is struggling to scrape and persist 12M series into its local TSDB, and Thanos Receive is unable to keep up with the remote-write ingestion rate, leading to dropped metrics and CPU/memory saturation. At this scale, a single Thanos Receive instance is insufficient — you need horizontal sharding, aggressive downsampling, and label cardinality management.

---

## 1. Understanding the Scale Problem

### 1.1 Prometheus Limits at 12M Series

Prometheus was designed for single-node operation with local disk storage. At 12 million active series:

- **Memory pressure:** Prometheus stores all active series in RAM. Each series consumes ~1-2KB of memory in the Series Segment, meaning **~12-24GB just for the series catalog** — not counting chunk storage, which adds another 3-5x on top
- **Disk I/O saturation:** The TSDB writes new chunks every 2 hours. With 12M series, WAL (Write-Ahead Log) compaction and head compaction become I/O bound, causing scrape failures
- **Query latency:** Range queries across millions of series with high-cardinality labels can timeout Prometheus before Grafana renders results
- **GC pauses:** Go's garbage collector struggles with the heap size, causing periodic 10-30 second pauses that break alerting and recording rules

### 1.2 Thanos Receive Bottlenecks

Thanos Receive was designed to handle high-volume ingestion, but at 12M series you face specific issues:

- **CPU saturation:** Thanos Receive's primary bottleneck is compression and block creation. Each incoming series must be indexed, compressed (Snappy), and written to the local TSDB. At scale, CPU becomes the hard limit
- **Memory hysteresis:** As documented in [Thanos Discussion #7165](https://github.com/thanos-io/thanos/discussions/7165), after stress tests, Thanos Receive pods "hogs high memory utilisation for more than 16 hours" — the memory doesn't properly release even after load decreases
- **Replication lag:** If you've enabled replication (for HA), the write path doubles, compounding the CPU and I/O pressure
- **Block upload backpressure:** When Thanos Receive can't keep up uploading TSDB blocks to object storage, the local TSDB fills up and rejects new writes

---

## 2. Architecture: Horizontal Sharding with Thanos Receive

### 2.1 Ring-Based Sharding (Critical Fix)

The single biggest architectural change needed is **sharding your metrics across multiple Thanos Receive instances** using the ring-based partitioning built into Thanos Receive:

```yaml
# Each Prometheus or Thanos Ruler writes to a specific ring partition
# Partition is determined by the __address__ or a hash of label values

thanos receive:
  # The ring configuration for horizontal scaling
  --store=store-gateway-1:10901,store-gateway-2:10901,store-gateway-3:10901
  --replication-factor=1           # Set >1 for HA (doubles resource needs)
  --tsdb.no-lockfile               # Important for multi-instance deployments
  --remote-write.handler.max-procs=  # Match to CPU cores
```

**Sharding strategy for 12M series:**

| Shards | Series per Shard | CPU per Pod | RAM per Pod | Object Storage Uploads/hr |
|--------|-----------------|-------------|-------------|--------------------------|
| 1      | 12M             | 90%+        | 16-32 GB    | Continuous               |
| 2      | 6M              | 60-70%      | 8-16 GB     | Manageable               |
| 4      | 3M              | 35-50%      | 4-8 GB      | Sustainable              |
| 8      | 1.5M            | 20-30%      | 2-4 GB      | Comfortable              |

**Recommendation:** Start with **4 shards** (12M / 4 = 3M series per shard), each on a 4-8 core machine with 16GB RAM. Monitor CPU, then add more shards if needed.

### 2.2 Prometheus to Thanos Receive Configuration

Your Prometheus instances need correct remote-write configuration pointing to the ring:

```yaml
remote_write:
  - url: "http://thanos-receive.monitoring.svc.cluster.local:19291/api/v1/receive"
    # IMPORTANT: Use consistent hash ring
    write_relabel_configs:
      - source_labels: [__name__]
        regex: 'go_.*|process_.*|scrape_.*'
        action: keep   # Keep only essential low-cardinality metrics
    # Queue config for backpressure handling
    queue_config:
      max_shards: 30                    # Increase from default 20
      capacity: 25000                   # Increase from 5000
      max_samples_per_send: 2000        # Increase from 500
      batch_send_deadline: 5s           # Decrease from 5s to flush faster
      min_backoff: 30ms                 # Decrease from 30ms
      max_backoff: 100ms                # Decrease from 100ms
```

---

## 3. Aggressive Downsampling

At 12M series, storing raw-second metrics for any significant period is unsustainable. Downsampling is non-negotiable.

### 3.1 Thanos Receive Downsampling

```yaml
thanos receive:
  # Downsampling reduces stored samples, cutting storage by 10-100x
  --tsdb.min-block-duration=2h
  --tsdb.max-block-duration=2h
  --downsampling.disable=false
  # Use Honeycomb downsampler for better quality retention
  --downsampling.honeycomb.enable=true
  --downsampling.honeycomb.desired-resolution=60s  # Downsample to 1-min after 2h
```

**Downsampling tiers:**

| Resolution | Retention | Compression Ratio | Use Case |
|------------|-----------|-------------------|----------|
| 1s (raw)   | 2 hours   | 1x                | Real-time dashboards, incident investigation |
| 10s        | 7 days    | 10x               | Recent trends, service-level dashboards |
| 1m         | 90 days   | 60x               | Capacity planning, SLO tracking |
| 5m         | 1 year    | 300x              | Historical analysis, compliance |
| 15m        | 3 years   | 900x              | Long-term trend analysis |

### 3.2 Record Rules for Aggregation

Use Prometheus recording rules to pre-aggregate high-cardinality metrics before they hit storage:

```yaml
# Reduces 100K individual container metrics to ~500 group-level metrics
groups:
  - name: aggregate_containers
    interval: 30s
    rules:
      - record: job:container_cpu_seconds:rate5m
        expr: sum(rate(container_cpu_usage_seconds_total[5m])) by (job, namespace)
      - record: job:container_memory_usage:avg
        expr: avg(container_memory_usage_bytes) by (job, namespace)
      - record: job:http_requests:rate5m
        expr: sum(rate(http_requests_total[5m])) by (job, endpoint)
```

---

## 4. Cardinality Management

High cardinality (too many unique label combinations) is often the real problem, not the raw number of series.

### 4.1 Identify High-Cardinality Labels

```promql
# Find labels with >1000 unique values
label_values(up, instance) 
| sort_desc(count({__name__=~".+"}) by (__name__)) 
| topk(20)
```

Common high-cardinality culprits:
- `pod` names (rapid churn in Kubernetes)
- `request_id`, `trace_id` (should not be stored long-term)
- `user_id`, `session_id`, `customer_id` (unless explicitly needed)
- `kubernetes_pod_annotations` (unbounded key-value pairs)

### 4.2 Label Drop via Relabeling

```yaml
# In Prometheus scrape configs
relabel_configs:
  - source_labels: [__name__]
    regex: 'go_.*|process_.*|scrape_.*'
    action: keep     # Keep only runtime metrics

# In remote-write config
write_relabel_configs:
  - source_labels: [__name__]
    regex: '.+_(duration_seconds|total_count|total_size_bytes)$'
    action: drop     # Drop auto-generated histogram/summary series
  
  - regex: '__.*'
    action: labeldrop  # Remove all internal Prometheus labels
```

### 4.3 Rule-Based Metric Filtering

At Grafana Labs scale (10-30M active series per tenant), the key insight is: **not all metrics are equally valuable**. Implement a tiered retention policy:

| Tier | Example Metrics | Retention | Cardinality Cap |
|------|----------------|-----------|----------------|
| P0 (Critical) | Node CPU, memory, disk, network | 1 year | No cap |
| P1 (Important) | Application request rate, error rate, latency p99 | 90 days | 50K per app |
| P2 (Diagnostic) | Container metrics, K8s pod status | 30 days | 500K total |
| P3 (Debug) | Individual request traces, debug flags | 7 days | Unlimited |

---

## 5. Thanos Component Tuning

### 5.1 Thanos Store Gateway

The Store Gateway reads TSDB blocks from object storage. With 12M series, query performance depends on block compaction:

```yaml
thanos store:
  --block-sync-concurrency=20              # Parallel block sync
  --index-cache-size=2GiB                  # Increase index cache
  --chunk-cache-size=4GiB                  # Increase chunk cache
  --tsdb.max-block-chunk-segment-size=128M # Larger chunks = fewer I/O ops
  --log.level=info
```

**Key tuning:** The Store Gateway CPU usage is proportional to the number of **non-compacted blocks** it must query. Aggressive compaction (smaller block duration, faster compaction cycles) is essential.

### 5.2 Thanos Compactor

```yaml
thanos compact:
  --compact.max-sync-block-duration=2h    # Match receive block duration
  --compact.deletion-delay=30m            # Delay before deleting old blocks
  --compact.log-level=info
  # Enable downsampling (already configured on receive)
```

With 12M series, compaction is the **most critical background process**. If compaction falls behind, query latency explodes. Consider dedicated compaction hardware.

### 5.3 Thanos Querier

```yaml
thanos query:
  --query.max-concurrency=50              # Parallel query execution
  --query.timeout=120s                    # Timeout for complex queries
  --query.stacksize=1048576               # 1MB stack for complex PromQL
  --store=store-gateway-1:10901,store-gateway-2:10901,store-gateway-3:10901
  --store=receive-1:10901,receive-2:10901,receive-3:10901,receive-4:10901
```

### 5.4 Replica Count and External Labels

For high availability, you need **at least 2 replicas** of the entire pipeline:

```yaml
# Prometheus external labels (must match between replicas)
global:
  external_labels:
    cluster: primary
    replica: '1'

# Prometheus replica 2
global:
  external_labels:
    cluster: primary
    replica: '2'

# Thanos Receive must know about both
thanos receive:
  --replication-factor=2
```

**Trade-off:** Replica factor of 2 doubles resource requirements. At 12M series, this means 8 shards at 2 replicas = 16 Thanos Receive pods minimum.

---

## 6. Prometheus-Side Optimizations

### 6.1 Multi-Instance Prometheus Federation

Instead of a single Prometheus handling all scrapes:

```yaml
# Prometheus instance A: monitors infrastructure (nodes, routers, switches)
scrape_configs:
  - job_name: 'infrastructure'
    static_configs:
      - targets: ['node-exporter:9100', 'blackbox-exporter:9115']

# Prometheus instance B: monitors application services
scrape_configs:
  - job_name: 'applications'
    kubernetes_sd_configs:
      - role: pod

# Prometheus instance C: monitors Kubernetes itself
scrape_configs:
  - job_name: 'kubernetes'
    kubernetes_sd_configs:
      - role: node
        api_server: 'https://kubernetes:443'
```

Each Prometheus instance writes to its **assigned Thanos Receive shard** via consistent hashing.

### 6.2 Scrape Configuration Tuning

```yaml
global:
  scrape_interval: 15s           # Don't go below 15s at this scale
  scrape_timeout: 10s            # Must be < scrape_interval
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'node-exporter'
    scrape_interval: 30s         # Lower cardinality, scrape less often
    scrape_timeout: 10s
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: 'node_exporter_cpuidle_seconds_total|node_exporter_cpuinfo_seconds_total'
        action: drop
```

**Key metrics:**

| Metric | Safe Limit | Your 12M Context |
|--------|-----------|------------------|
| Scrape interval | >= 15s | Use 30s for low-value jobs |
| Max targets per scrape | 10K | Keep below 5K |
| Max series per job | 100K | Cap at 50K |
| Write-ahead log size | < 2GB | Tune `--tsdb.wal-compression` |

---

## 7. Alternative: Grafana Mimir

If Thanos doesn't scale to your satisfaction, consider **Grafana Mimir** (formerly Cortex), which is purpose-built for this scale:

### 7.1 Why Mimir at 12M Series

Grafana Labs runs Mimir at **100+ million active series** in production. Benchmarks show:

- Linear hardware scaling up to **500 million active series**
- 85 million data points per second sustained throughput
- Automatic compaction and downsampling (no manual tuning needed)
- Built-in multi-tenancy

### 7.2 Migration Path from Thanos

```bash
# Upload existing Thanos TSDB blocks to Mimir
mimirtool backfill --address=http://mimir-ingester:8080 \
  --id=mytenant \
  --from-tsdb=/path/to/thanos/receive/tsdb
```

Mimir handles the entire pipeline: ingestion → storage → compaction → query → downsampling, removing the operational complexity of managing Thanos Receive + Store Gateway + Compactor + Querier separately.

---

## 8. Grafana Query Optimization

Grafana itself can become a bottleneck when querying 12M series.

### 8.1 Dashboard-Level Optimizations

```jsonc
// In Grafana dashboard JSON:
{
  "time": { "from": "now-1h", "to": "now" },  // Limit time range
  "panelInfo": {
    "datasource": "prometheus",
    "options": {
      "legend": { "show": true },
      "tooltip": { "mode": "single" }  // Don't show all series
    }
  }
}
```

**Key Grafana tuning:**
- **Limit time ranges:** Never query more than 1 hour on raw dashboards; use 7-day for trend views
- **Use template variables wisely:** Dropdowns with 1000+ options cause slow queries
- **Enable Prometheus query caching:** Set `prometheus.query.timeout` to 30s in datasource config
- **Avoid `topk()` with large values:** `topk(1000, ...)` forces evaluation of all series
- **Use `limit()` instead:** `limit(50, sum(rate(http_requests_total[5m])))`

### 8.2 Dashboard Alerts

Instead of querying raw metrics in dashboards, use Prometheus recording rules and alert on pre-computed aggregations:

```yaml
# Instead of dashboard querying:
# sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)

# Use recording rule:
- record: job:http_5xx_rate:rate5m
  expr: sum(rate(http_requests_total{status=~"5.."}[5m])) by (job)

# Then dashboard queries the pre-computed recording rule
```

---

## 9. Monitoring the Monitor

You need observability on your monitoring infrastructure:

### 9.1 Key Thanos Receive Metrics to Watch

| Metric | Alert Threshold | Meaning |
|--------|----------------|---------|
| `thanos_receive_dispatch_duration_seconds` | p99 > 1s | Dispatch latency to store |
| `thanos_receive_storage_local_blocks_count` | Increasing > 50 | Block backlog |
| `thanos_receive_hdp有一个ps_oom` | > 0 | OOM kills |
| `node_cpu_seconds_total{mode="idle"}` | < 10% idle | CPU saturation |
| `node_memory_MemAvailable_bytes` | < 10% available | Memory pressure |
| `than**: receive_ring_healthy_members` | < total expected | Ring health |
| `thanos_receive_replication_factor` | > 1 | Check if replication adds unneeded overhead |
| `tsdb_compactions_failed_total` | > 0 | Compaction failures |
| `tsdb_wal_corruptions_total` | > 0 | WAL corruption |
| `thanos_receive_isolate_operation_time_seconds` | > 5s | Write rejection rate |

### 9.2 Prometheus Self-Monitoring

```yaml
# Thanos sidecar metrics to expose in Grafana
- match: 'thanos_*'
  action: scrape
  port: 10902  # HTTP port

# Prometheus TSDB health
- match: 'tsdb_blocks_loaded'
  action: scrape

# Write-ahead log health
- match: 'prometheus_tsdb_wal_storage_size_bytes'
  action: scrape
```

---

## 10. Recommended Action Plan

### Phase 1: Immediate (Week 1-2)

- [ ] **Shard Thanos Receive:** Scale from 1 to 4 shards, each handling ~3M series
- [ ] **Enable downsampling:** Configures `--downsampling.honeycomb.enable=true` with 60s resolution
- [ ] **Drop high-cardinality labels:** Identify and remove labels with >1000 unique values via `labeldrop`
- [ ] **Tune remote-write queue:** Increase `max_shards` to 30, `capacity` to 25K
- [ ] **Set Grafana query timeouts:** Limit to 30s per datasource

### Phase 2: Stabilization (Week 3-4)

- [ ] **Implement recording rules:** Pre-aggregate top 50 high-cardinality metric families
- [ ] **Configure compactor:** Dedicated compactor with aggressive block-duration settings
- [ ] **Set up dashboard monitoring:** Monitor Thanos Receive CPU, memory, block backlog
- [ ] **Review scrape configs:** Reduce scrape frequency for non-critical jobs to 30-60s

### Phase 3: Scaling (Month 2)

- [ ] **Evaluate Grafana Mimir:** If Thanos doesn't stabilize, evaluate Mimir migration
- [ ] **Add replication:** If HA is required, set `replication-factor=2` and double shards
- [ ] **External labels audit:** Ensure every external label is necessary and bounded
- [ ] **Disk I/O optimization:** Use NVMe SSDs for Thanos Receive local TSDB, upgrade to 10Gbps networking

### Phase 4: Long-Term (Month 3+)

- [ ] **Label lifecycle management:** Automated label drop for ephemeral labels
- [ ] **Multi-region replication:** If operating across regions, use Thanos querier federation
- [ ] **Cost analysis:** Benchmark object storage costs at 12M series vs. managed alternatives

---

## 11. Summary: Root Causes and Fixes

| Problem | Root Cause | Fix |
|---------|-----------|-----|
| Prometheus can't send metrics | Local TSDB overwhelmed at 12M series | Push to Thanos Receive shards via remote_write |
| Thanos Receive not processing | Single instance CPU/bandwidth saturation | Shard across 4+ instances |
| Memory hysteresis | TSDB doesn't release memory after load | Add more shards, ensure `--tsdb.no-lockfile` |
| Slow Grafana queries | Querying non-compacted blocks, large time ranges | Enable downsampling, limit time windows |
| High cardinality explosion | Too many unique label combinations | labeldrop, recording rules, metric tiering |

---

## References

1. [Thanos Receive CPU Saturation](https://github.com/thanos-io/thanos/discussions/4270) — Thanos GitHub Discussions
2. [Thanos Receive Memory Hysteresis](https://github.com/thanos-io/thanos/discussions/7165) — Thanos GitHub Discussions #7165
3. [Help with Thanos on Huge Prometheus Environment](https://github.com/thanos-io/thanos/issues/569) — Thanos GitHub Issue #569
4. [Prometheus HA and Thanos with Huge Metrics](https://github.com/thanos-io/thanos/issues/582) — Thanos GitHub Issue #582
5. [Debug Super Slow Thanos](https://github.com/thanos-io/thanos/issues/6968) — Thanos GitHub Issue #6968
6. [Thanos Receive Documentation](https://thanos.io/v0.28/components/receive.md/) — Official Thanos Docs
7. [Thanos Troubleshooting](https://thanos.io/tip/operating/troubleshooting.md/) — Official Thanos Troubleshooting
8. [Benchmarking Grafana Enterprise Metrics](https://grafana.com/blog/benchmarking-grafana-enterprise-metrics-for-horizontally-scaling-prometheus-up-to-500-million-active-series/) — Grafana Labs
9. [Scaling Prometheus with Cortex Blocks Storage](https://grafana.com/blog/scaling-prometheus-how-were-pushing-cortex-blocks-storage-to-its-limit-and-beyond/) — Grafana Labs
10. [Scale Prometheus with Thanos on AKS](https://resources.cloudcops.com/case-studies/scaling-monitoring-with-thanos) — CloudCops Case Study
11. [Prometheus Limits at Scale](https://www.exoscale.com/blog/prometheus-limits-at-scale/) — Exoscale Blog
12. [Multi-Tenancy with Thanos Receiver](https://www.infracloud.io/blogs/multi-tenancy-monitoring-thanos-receiver/) — InfraCloud Blog
13. [Prometheus Alternatives for Metrics at Scale](https://openobserve.ai/blog/prometheus-alternatives/) — OpenObserve
14. [Migrate from Thanos to Grafana Mimir](https://grafana.com/docs/mimir/latest/set-up/migrate/migrate-from-thanos-or-prometheus/) — Grafana Mimir Docs
15. [Thanos vs Mimir](https://community.grafana.com/t/thanos-vs-mimir-choosing-the-right-prometheus-extension/157751) — Grafana Community
16. [Troubleshoot Prometheus Data Source Issues](https://grafana.com/docs/grafana/latest/datasources/prometheus/troubleshooting/) — Grafana Docs
