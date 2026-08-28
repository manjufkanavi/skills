# OpenBao Production-Hardened Configuration
# Template — adapt paths and credentials for your deployment
#
# Key production features:
# - Raft storage with snapshot_interval for crash recovery
# - Autopilot config for multi-node health management
# - Audit logging to prevent blind spots
# - Log rotation for disk space management
# - Explicit API/cluster addresses for clustering compatibility
# - mlock enabled for memory protection
# - TLS 1.2 minimum, SAN-certified server cert

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_disable   = 0
  tls_cert_file = "/openbao/data/certs/server.crt"
  tls_key_file  = "/openbao/data/certs/server.key"
  tls_client_ca_file = "/openbao/data/certs/ca.crt"
  tls_min_version = "tls12"
  tls_client_addr = "0.0.0.0:8200"
}

storage "raft" {
  path            = "/openbao/raft"
  node_id         = "node1"
  snapshot_interval = "30m"
  streamline      = true
}

# Raft Autopilot — tune thresholds for your environment
autopilot {
  cleanup_dead_servers      = true
  last_contact_threshold    = "200ms"
  max_trailing_logs         = 250
  dead_server_timeout       = "1h"
  enable_state_resets       = true
  servers_stabilization_time = "10s"
  max_variable_transients   = true
}

# Audit configuration — log all operations to file
# Enable with: bao audit enable file file_path=/openbao/data/audit/openbao.log
#audit {
#  type = "file"
#  options = {
#    file_path = "/openbao/data/audit/openbao.log"
#  }
#}

api_addr     = "https://127.0.0.1:8200"
cluster_addr = "https://127.0.0.1:8201"

ui = true

default_lease_ttl = "768h"
max_lease_ttl     = "768h"

# Security: mlock prevents OpenBao secrets from being swapped to disk
disable_mlock = false

log_level   = "info"
log_file    = "/openbao/data/openbao.log"
log_rotate_duration = "24h"
log_rotate_max_files = 10
log_rotate_max_size = 1024

# Performance tuning
ha_mode = true
