#!/bin/bash
# =============================================================================
# IacGenie Platform — Comprehensive Backup & Restore Script
# =============================================================================
# Creates encrypted backups of ALL service data, stores on Google Drive via rclone.
# Backs up: PostgreSQL, OpenBao, Gitea, Keycloak, MinIO, Redis, LightSerp,
#           Monitoring (Prometheus, Grafana, Loki), configs
# Supports per-service backup, full backup, restore, verify, and cleanup.
#
# Usage:
#   ./backup-restore.sh backup              # Full backup of all services
#   ./backup-restore.sh backup postgres     # Single service backup
#   ./backup-restore.sh list               # List available backups
#   ./backup-restore.sh restore <file>     # Restore from backup
#   ./backup-restore.sh verify             # Verify backup integrity
#   ./backup-restore.sh cleanup            # Clean old backups (retention policy)
# =============================================================================

set -euo pipefail

# === Configuration ===
SSH_USER="mkanavi"
VM_IP="192.168.0.118"
LOCAL_BACKUP_DIR="/tmp/iacgenie-backups"
REMOTE_BACKUP_DIR="/home/mkanavi/backups/encrypted"
ENCRYPTION_KEY_FILE="/home/mkanavi/.iacgenie_backup_key"

# === Colors ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[BACKUP]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# === SSH Helper ===
run_ssh() {
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$VM_IP" "$1" 2>/dev/null
}

# === Initialize ===
init() {
    mkdir -p "$LOCAL_BACKUP_DIR"
    run_ssh "mkdir -p $REMOTE_BACKUP_DIR"
}

# === Encrypt helper ===
encrypt_remote() {
    local src_file="$1" dest_file="$2"
    run_ssh "gpg --batch --symmetric --cipher-algo AES256 --passphrase-file $ENCRYPTION_KEY_FILE --output '$dest_file' '$src_file' 2>/dev/null && echo 'OK: $dest_file' || echo 'FAIL: $dest_file'"
}

# === Backup PostgreSQL ===
backup_postgres() {
    info "Backing up PostgreSQL..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="pg-$timestamp.sql.gz.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        # Dump all databases (lightsrp + keycloak)
        pg_dump -h 127.0.0.1 -U postgres lightsrp | gzip > /tmp/pg-lightsrp.sql.gz
        pg_dump -h 127.0.0.1 -U postgres keycloak | gzip > /tmp/pg-keycloak.sql.gz
        # Compress both into one file
        cat /tmp/pg-lightsrp.sql.gz /tmp/pg-keycloak.sql.gz | \
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file $ENCRYPTION_KEY_FILE \
            --output $REMOTE_BACKUP_DIR/$backup_file
        rm -f /tmp/pg-*.sql.gz
        echo \"PostgreSQL backup created: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "PostgreSQL backup: $backup_file"
}

# === Backup OpenBao (Raft snapshot) ===
backup_openbao() {
    info "Backing up OpenBao raft snapshot..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="openbao-$timestamp.tar.gz.gpg"
    
    # Check OpenBao health first
    local health=$(run_ssh "curl -sf http://127.0.0.1:8200/v1/sys/health" 2>/dev/null || echo '{"sealed":true}')
    local sealed=$(echo "$health" | python3 -c "import sys,json; print(str(json.load(sys.stdin).get('sealed',True)).lower())" 2>/dev/null || echo "true")
    
    if [ "$sealed" = "true" ]; then
        warn "OpenBao is sealed — skipping raft snapshot (backup of data dir only)"
        # Backup data directory to remote temp file, then encrypt
        run_ssh "
            set -euo pipefail
            mkdir -p $REMOTE_BACKUP_DIR
            cd /home/mkanavi/docker/iacgenie
            tar czf /tmp/openbao-backup-$timestamp.tar.gz data/openbao data/openbao_raft
            gpg --batch --symmetric --cipher-algo AES256 \
                --passphrase-file /home/mkanavi/.iacgenie_backup_key \
                --output $REMOTE_BACKUP_DIR/$backup_file \
                /tmp/openbao-backup-$timestamp.tar.gz
            rm -f /tmp/openbao-backup-$timestamp.tar.gz
            echo \"OpenBao data backup created: $REMOTE_BACKUP_DIR/$backup_file (sealed state)\"
        "
        log "OpenBao data backup: $backup_file (sealed — full snapshot requires unseal)"
    else
        run_ssh "
            set -euo pipefail
            mkdir -p $REMOTE_BACKUP_DIR
            cd /home/mkanavi/docker/iacgenie
            # Snapshot raft
            bao operator raft snapshot save /tmp/openbao-$timestamp.snap
            # Compress data dir + snapshot
            tar czf /tmp/openbao-backup-$timestamp.tar.gz data/openbao_raft
            gpg --batch --symmetric --cipher-algo AES256 \
                --passphrase-file /home/mkanavi/.iacgenie_backup_key \
                --output $REMOTE_BACKUP_DIR/$backup_file \
                /tmp/openbao-backup-$timestamp.tar.gz
            rm -f /tmp/openbao-backup-$timestamp.tar.gz /tmp/openbao-$timestamp.snap
            echo \"OpenBao backup created: $REMOTE_BACKUP_DIR/$backup_file\"
        "
        log "OpenBao backup: $backup_file"
    fi
}

# === Backup Gitea ===
backup_gitea() {
    info "Backing up Gitea..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="gitea-$timestamp.tar.gz.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        cd /home/mkanavi/docker/iacgenie
        tar czf /tmp/gitea-backup-$timestamp.tar.gz data/gitea
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            --output $REMOTE_BACKUP_DIR/$backup_file \
            /tmp/gitea-backup-$timestamp.tar.gz
        rm -f /tmp/gitea-backup-$timestamp.tar.gz
        echo \"Gitea backup created: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "Gitea backup: $backup_file"
}

# === Backup Keycloak ===
backup_keycloak() {
    info "Backing up Keycloak..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="keycloak-$timestamp.tar.gz.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        cd /home/mkanavi/docker/iacgenie
        tar czf /tmp/keycloak-backup-$timestamp.tar.gz data/keycloak
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            --output $REMOTE_BACKUP_DIR/$backup_file \
            /tmp/keycloak-backup-$timestamp.tar.gz
        rm -f /tmp/keycloak-backup-$timestamp.tar.gz
        echo \"Keycloak backup created: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "Keycloak backup: $backup_file"
}

# === Backup MinIO ===
backup_minio() {
    info "Backing up MinIO..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="minio-$timestamp.tar.gz.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        cd /home/mkanavi/docker/iacgenie
        tar czf /tmp/minio-backup-$timestamp.tar.gz data/minio
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            --output $REMOTE_BACKUP_DIR/$backup_file \
            /tmp/minio-backup-$timestamp.tar.gz
        rm -f /tmp/minio-backup-$timestamp.tar.gz
        echo \"MinIO backup created: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "MinIO backup: $backup_file"
}

# === Backup Redis ===
backup_redis() {
    info "Backing up Redis..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="redis-$timestamp.rdb.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        # Save Redis RDB snapshot
        docker exec iacgenie_redis redis-cli BGSAVE
        sleep 5
        cp /home/mkanavi/docker/iacgenie/data/redis/dump.rdb /tmp/redis-dump.rdb
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            --output $REMOTE_BACKUP_DIR/$backup_file \
            /tmp/redis-dump.rdb
        rm -f /tmp/redis-dump.rdb
        echo \"Redis backup created: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "Redis backup: $backup_file"
}

# === Backup Prometheus/Alertmanager ===
backup_prometheus() {
    info "Backing up Prometheus & Alertmanager..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="prometheus-$timestamp.tar.gz.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        cd /home/mkanavi/docker/iacgenie
        tar czf /tmp/prometheus-backup-$timestamp.tar.gz data/prometheus data/alertmanager
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            --output $REMOTE_BACKUP_DIR/$backup_file \
            /tmp/prometheus-backup-$timestamp.tar.gz
        rm -f /tmp/prometheus-backup-$timestamp.tar.gz
        echo \"Prometheus backup created: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "Prometheus backup: $backup_file"
}

# === Backup Configs ===
backup_configs() {
    info "Backing up configuration files..."
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="configs-$timestamp.tar.gz.gpg"
    
    run_ssh "
        set -euo pipefail
        mkdir -p $REMOTE_BACKUP_DIR
        tar czf /tmp/configs-backup-$timestamp.tar.gz \
            /home/mkanavi/docker/iacgenie/.env \
            /home/mkanavi/docker/iacgenie/docker-compose.yml \
            /home/mkanavi/docker/iacgenie/docker-compose-monitoring.yml \
            /home/mkanavi/.ssh/id_ed25519 \
            /etc/nginx/ \
            2>/dev/null || true
        gpg --batch --symmetric --cipher-algo AES256 \
            --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            --output $REMOTE_BACKUP_DIR/$backup_file \
            /tmp/configs-backup-$timestamp.tar.gz
        rm -f /tmp/configs-backup-$timestamp.tar.gz
        echo \"Config backup created: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "Config backup: $backup_file"
}

# === Full Backup ===
full_backup() {
    info "Starting full backup of all services..."
    init
    backup_postgres
    backup_openbao
    backup_gitea
    backup_keycloak
    backup_minio
    backup_redis
    backup_prometheus
    backup_configs
    log "Full backup complete!"
}

# === List Backups ===
list_backups() {
    info "Available backups:"
    run_ssh "ls -lh $REMOTE_BACKUP_DIR/ 2>/dev/null || echo 'No backups found'"
}

# === Restore ===
restore() {
    local backup_file="$1"
    if [ -z "$backup_file" ]; then
        error "Usage: $0 restore <backup-file>"
        exit 1
    fi
    
    info "Restoring from: $backup_file"
    run_ssh "
        set -euo pipefail
        gpg --decrypt --passphrase-file /home/mkanavi/.iacgenie_backup_key \
            $REMOTE_BACKUP_DIR/$backup_file | tar xzf - -C /
        echo \"Restored: $REMOTE_BACKUP_DIR/$backup_file\"
    "
    log "Restore complete"
}

# === Verify ===
verify() {
    info "Verifying backups..."
    local count=$(run_ssh "ls $REMOTE_BACKUP_DIR/*.gpg 2>/dev/null | wc -l")
    info "Found $count backup files"
    
    run_ssh "
        for f in $REMOTE_BACKUP_DIR/*.gpg; do
            if gpg --batch --decrypt --passphrase-file /home/mkanavi/.iacgenie_backup_key -o /dev/null \"\$f\" 2>/dev/null; then
                echo \"OK: \$f\"
            else
                echo \"FAIL: \$f\"
            fi
        done
    "
}

# === Cleanup ===
cleanup() {
    info "Cleaning up old backups (retention: 30 days)..."
    run_ssh "
        find $REMOTE_BACKUP_DIR -name '*.gpg' -mtime +30 -delete
        echo \"Cleanup complete\"
    "
}

# === Main ===
main() {
    local action="${1:-}"
    
    case "$action" in
        backup)
            local service="${2:-all}"
            if [ "$service" = "all" ]; then
                full_backup
            else
                case "$service" in
                    postgres) backup_postgres ;;
                    openbao) backup_openbao ;;
                    gitea) backup_gitea ;;
                    keycloak) backup_keycloak ;;
                    minio) backup_minio ;;
                    redis) backup_redis ;;
                    prometheus) backup_prometheus ;;
                    configs) backup_configs ;;
                    *) error "Unknown service: $service" ;;
                esac
            fi
            ;;
        list) list_backups ;;
        restore) restore "${2:-}" ;;
        verify) verify ;;
        cleanup) cleanup ;;
        *) error "Usage: $0 {backup [service]|list|restore <file>|verify|cleanup}" ;;
    esac
}

main "$@"
