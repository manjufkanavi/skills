#!/usr/bin/env python3
"""
OpenBao Backup Fallback — direct vault.db copy from host bind mount.
Use when the API snapshot fails (Connection reset, timeout, permission denied, etc.).

This script bypasses the OpenBao HTTP API entirely and copies the Raft database
file directly from the host filesystem. It is the most reliable backup method
when the Docker port proxy is dropping connections.

Usage:
    python3 backup_openbao_fallback.py

Environment:
    OPENBAO_BACKUP_DIR  — Override backup directory (default: <compose_dir>/openbao_raft/backups)
    COMPOSE_DIR         — Override compose directory (default: /home/mkanavi/docker/iacgenie)
"""

import os, shutil, datetime, hashlib, sys, time

# ── Configuration ──────────────────────────────────────────────────────────
COMPOSE_DIR = os.getenv("COMPOSE_DIR", "/home/mkanavi/docker/iacgenie")
RAFT_DIR = os.path.join(COMPOSE_DIR, "openbao_raft")
BACKUP_DIR = os.getenv("OPENBAO_BACKUP_DIR", os.path.join(RAFT_DIR, "backups"))
VAULT_DB = os.path.join(RAFT_DIR, "vault.db")
KEEP_DAYS = 30

def log(msg=""):
    print(msg)

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def rotate_backups():
    """Remove backups older than KEEP_DAYS."""
    now = time.time()
    for f in os.listdir(BACKUP_DIR):
        fpath = os.path.join(BACKUP_DIR, f)
        if os.path.isfile(fpath) and os.path.getmtime(fpath) < now - KEEP_DAYS * 86400:
            os.remove(fpath)

def backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)

    if not os.path.exists(VAULT_DB):
        log(f"ERROR: vault.db not found at {VAULT_DB}")
        sys.exit(1)

    # Copy vault.db
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
    dest = os.path.join(BACKUP_DIR, f"vault.db-{ts}")
    shutil.copy2(VAULT_DB, dest)

    size = os.path.getsize(dest)
    checksum = sha256_file(dest)

    log(f"[OK] Fallback Backup: vault.db-{ts}")
    log(f"  Size: {size:,} bytes ({size / 1024 / 1024:.1f} MB)")
    log(f"  SHA256: {checksum}")

    # Write .sha256 checksum file
    with open(f"{dest}.sha256", "w") as f:
        f.write(f"{checksum}  {dest}\n")
    log(f"  SHA256 file: {dest}.sha256")

    # Copy config if present
    for cfg_path in [
        os.path.join(RAFT_DIR, "openbao-prod.hcl"),
        os.path.join(COMPOSE_DIR, "data/openbao", "openbao-prod.hcl"),
        os.path.join(COMPOSE_DIR, "openbao_raft", "openbao-prod.hcl"),
    ]:
        if os.path.exists(cfg_path):
            cfg_dest = os.path.join(BACKUP_DIR, f"openbao-config-{ts}.hcl")
            shutil.copy2(cfg_path, cfg_dest)
            log(f"  Config backup: {cfg_dest}")
            break

    # Rotate old backups
    rotate_backups()

    log(f"  Rotated backups (kept last {KEEP_DAYS} days)")
    log("Backup completed successfully.")

if __name__ == "__main__":
    backup()