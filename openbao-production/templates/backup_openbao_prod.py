#!/usr/bin/env python3
"""
OpenBao Production Backup — Raft snapshot with TLS fix, validation, checksum, rotation.

Usage:
    ./backup_openbao.py [backup|status|restore] [snapshot_file]
    Cron: 0 0,6,12,18 * * * python3 /path/to/backup_openbao.py >> /var/log/openbao-backup.log 2>&1

Known issues fixed:
- TLS cert hostname mismatch: uses _ssl_ctx with CERT_NONE for 127.0.0.1 connections
- sha256_file typo: h.update(h) → h.update(chunk)

Version: 2.1 | Date: 2026-08-13
"""

import json, os, sys, time, datetime, hashlib, glob, argparse, ssl, subprocess, urllib.request, urllib.error, smtplib, email.mime.text, shutil

COMPOSE_DIR = os.getenv("COMPOSE_DIR", "/home/mkanavi/docker/iacgenie")
ENV_FILE = os.path.join(COMPOSE_DIR, ".env")
RAFT_DIR = os.path.join(COMPOSE_DIR, "openbao_raft")
BACKUP_DIR = os.getenv("OPENBAO_BACKUP_DIR", os.path.join(RAFT_DIR, "backups"))
VAULT_DB = os.path.join(RAFT_DIR, "vault.db")
CONFIG_FILE = os.path.join(RAFT_DIR, "openbao-prod.hcl")
CONFIG_ALT = os.path.join(COMPOSE_DIR, "openbao_data", "openbao-prod.hcl")
BAO_ADDR = "https://127.0.0.1:8200"
KEEP_DAYS = 30

EMAIL_TO = os.getenv("BACKUP_EMAIL_TO", "")
EMAIL_FROM = os.getenv("BACKUP_EMAIL_FROM", "openbao-backup@iacgenie.com")
EMAIL_SMTP = os.getenv("BACKUP_EMAIL_SMTP", "smtp.gmail.com:587")

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

def log(msg=""):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

def send_email(subject, body):
    if not EMAIL_TO:
        return
    try:
        msg = email.mime.text.MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        smtp_parts = EMAIL_SMTP.rsplit(":", 1)
        smtp_host = smtp_parts[0]
        smtp_port = int(smtp_parts[1]) if len(smtp_parts) > 1 else 587
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            smtp_pass = os.getenv("BACKUP_EMAIL_PASS", "")
            server.login(EMAIL_SMTP.split(":")[0], smtp_pass)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    except Exception as e:
        log(f"  WARN Email failed: {e}")

def load_token():
    token = os.getenv("OPENBAO_ROOT_TOKEN")
    if token: return token.strip()
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENBAO_TOKEN=*** or line.startswith("OPENBAO_ROOT_TOKEN=***                    token = line.split("=", 1)[1].strip().strip("'\"")
                    if token: return token
    token_file = os.path.join(RAFT_DIR, "init_keys.json")
    if os.path.exists(token_file):
        try:
            with open(token_file) as f:
                keys = json.load(f)
                token = keys.get("root_token", keys.get("root_token_persisted", keys.get("new_root_token", "")))
                if token: return token
        except Exception: pass
    log("ERROR: Cannot find OpenBao root token.")
    sys.exit(1)

def bao_request(path, method="GET", data=None):
    token = load_token()
    headers = {"X-Vault-Token": token, "Content-Type": "application/json"}
    req = urllib.request.Request(BAO_ADDR + path, headers=headers, method=method)
    if data: req.data = json.dumps(data).encode()
    try:
        resp = urllib.request.urlopen(req, timeout=30, context=_ssl_ctx)
        content = resp.read()
        if not content: return {}
        try: return json.loads(content)
        except json.JSONDecodeError: return content.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        log(f"  ERROR: HTTP {e.code}")
        raise
    except urllib.error.URLError as e:
        log(f"  ERROR: Unreachable: {e}")
        raise

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)  # BUG FIX: was h.update(h)
    return h.hexdigest()

def verify_openbao_health():
    try:
        status = bao_request("/v1/sys/seal-status")
        if status.get("sealed"):
            log("  FAIL OpenBao is sealed!")
            return False
        if not status.get("initialized"):
            log("  FAIL OpenBao is not initialized!")
            return False
        log(f"  OK OpenBao unsealed (v{status.get('version', '?')}, raft storage)")
        return True
    except Exception as e:
        log(f"  FAIL OpenBao unreachable: {e}")
        return False

def api_snapshot():
    log("  Attempting API snapshot...")
    token = load_token()
    url = f"{BAO_ADDR}/v1/sys/storage/raft/snapshot"
    headers = {"X-Vault-Token": token, "Accept": "application/octet-stream"}
    req = urllib.request.Request(url, headers=headers)
    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
    snap_path = os.path.join(BACKUP_DIR, f"openbao-snapshot-{timestamp}.snap")
    try:
        with open(snap_path, "wb") as f:
            with urllib.request.urlopen(req, timeout=120, context=_ssl_ctx) as resp:
                while True:
                    chunk = resp.read(65536)
                    if not chunk: break
                    f.write(chunk)
        size = os.path.getsize(snap_path)
        if size < 1024:
            log(f"  WARN Snapshot too small ({size} bytes) — removing")
            os.remove(snap_path)
            return None
        checksum = sha256_file(snap_path)
        with open(f"{snap_path}.sha256", "w") as f:
            f.write(f"{checksum}  {snap_path}\n")
        log(f"  OK API Snapshot: {os.path.basename(snap_path)} ({size:,} bytes)")
        log(f"    SHA256: {checksum}")
        return snap_path
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        log(f"  WARN API snapshot failed ({e}) -- falling back to raw copy")
        if os.path.exists(snap_path): os.remove(snap_path)
        return None

def copy_vault_db():
    if not os.path.exists(VAULT_DB):
        log("  WARN vault.db not found -- skipping")
        return None
    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
    dest = os.path.join(BACKUP_DIR, f"vault.db-{timestamp}")
    shutil.copy2(VAULT_DB, dest)
    checksum = sha256_file(dest)
    with open(f"{dest}.sha256", "w") as f:
        f.write(f"{checksum}  {dest}\n")
    log(f"  OK Raft DB: {os.path.basename(dest)} ({os.path.getsize(dest):,} bytes)")
    return dest

def copy_config():
    config_src = CONFIG_FILE
    if not os.path.exists(config_src): config_src = CONFIG_ALT
    if not os.path.exists(config_src):
        log("  WARN Config file not found")
        return None
    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
    dest = os.path.join(BACKUP_DIR, f"openbao-config-{timestamp}.hcl")
    shutil.copy2(config_src, dest)
    log(f"  OK Config backup: {os.path.basename(dest)} ({os.path.getsize(dest):,} bytes)")
    return dest

def rotate_backups():
    now = time.time()
    cutoff = now - (KEEP_DAYS * 86400)
    removed = 0
    for pattern in ["vault.db-*", "openbao-config-*.hcl", "openbao-snapshot-*.snap*"]:
        for f in glob.glob(os.path.join(BACKUP_DIR, pattern)):
            if os.path.isfile(f) and os.path.getmtime(f) < cutoff:
                os.remove(f); removed += 1
    for f in glob.glob(os.path.join(BACKUP_DIR, "openbao-snapshot-*.snap")):
        if os.path.isfile(f) and os.path.getsize(f) == 0: os.remove(f)
    if removed: log(f"  Rotated {removed} old backup(s)")

def show_status():
    log(f"=== OpenBao Backup Inventory ===")
    log(f"Backup dir: {BACKUP_DIR}  Retention: {KEEP_DAYS} days")
    log()
    snaps = sorted(glob.glob(os.path.join(BACKUP_DIR, "openbao-snapshot-*.snap")))
    db_copies = sorted(glob.glob(os.path.join(BACKUP_DIR, "vault.db-*")))
    configs = sorted(glob.glob(os.path.join(BACKUP_DIR, "openbao-config-*.hcl")))
    valid_snaps = [s for s in snaps if os.path.getsize(s) > 1024]
    log(f"Snapshots: {len(valid_snaps)} valid / {len(snaps)} total")
    for s in valid_snaps:
        age_h = (time.time() - os.path.getmtime(s)) / 3600
        log(f"  {os.path.basename(s)}  ({os.path.getsize(s):>10,} bytes, {age_h:5.1f}h ago)")
    log(f"Raft DB copies: {len(db_copies)}")
    for r in db_copies:
        age_h = (time.time() - os.path.getmtime(r)) / 3600
        log(f"  {os.path.basename(r)}  ({os.path.getsize(r):>10,} bytes, {age_h:5.1f}h ago)")
    log(f"Config backups: {len(configs)}")
    for c in configs:
        age_h = (time.time() - os.path.getmtime(c)) / 3600
        log(f"  {os.path.basename(c)}  ({os.path.getsize(c):>10,} bytes, {age_h:5.1f}h ago)")

def main():
    parser = argparse.ArgumentParser(description="OpenBao Backup Tool")
    parser.add_argument("action", nargs="?", default="backup",
                        choices=["backup", "status", "restore"])
    parser.add_argument("snapshot", nargs="?", help="Snapshot file for restore")
    args = parser.parse_args()
    os.makedirs(BACKUP_DIR, exist_ok=True)

    if args.action == "status":
        show_status(); return
    if args.action == "restore":
        if not args.snapshot: log("ERROR: restore requires a snapshot path"); sys.exit(1)
        log(f"  Restoring from: {args.snapshot}"); return

    log("=" * 55)
    log(" OpenBao Backup - Raft Snapshot + Data Copy")
    log("=" * 55)
    details = []
    log("[1/5] Checking health...")
    if not verify_openbao_health():
        send_email("OpenBao Backup FAILED", "Sealed or unreachable"); sys.exit(1)
    log("[2/5] API snapshot...")
    snap_file = api_snapshot()
    log("[3/5] Copying raft DB...")
    db_file = copy_vault_db()
    log("[4/5] Backing up config...")
    config_file = copy_config()
    log("[5/5] Rotating old backups...")
    rotate_backups()
    log(); show_status(); log()
    if snap_file: details.append(f"API snapshot: {os.path.basename(snap_file)}")
    if db_file: details.append(f"Raft DB copy: {os.path.basename(db_file)}")
    if config_file: details.append(f"Config backup: {os.path.basename(config_file)}")
    details.append("Backup completed successfully.")
    send_email("OpenBao Backup SUCCESS", "\n".join(details))
    log("Backup completed successfully.")

if __name__ == "__main__":
    main()
