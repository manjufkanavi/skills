#!/usr/bin/env python3
"""
Scan .env files and other config for secret values.
Outputs a JSON catalog grouped by source and key.

Usage:
  python3 openbao-secret-scan.py --env-path /path/to/.env
  python3 openbao-secret-scan.py --all-repos --vm-host mkanavi@192.168.0.118
  python3 openbao-secret-scan.py --list-directories
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

SECRET_PATTERNS=***    r'(?:PASSWORD|PASSWD|PASS|SECRET|KEY|TOKEN|AUTH|CREDENTIAL|API_KEY|PRIVATE_KEY|CLIENT_SECRET|JWT_SECRET|REDIS_PASSWORD|DATABASE_URL)',
    r'(?:MONGO_URI|MONGODB_URI|MYSQL_ROOT_PASSWORD|POSTGRES_PASSWORD)',
    r'(?:SENTRY_DSN|SMTP.*PASSWORD|SMTP.*KEY|SMTP.*USERNAME)',
    r'(?:AWS_|GCP_|GEMINI|CLOUDFLARE|MINIO|LIGHTERP|OPENBAO)',
]

SECRET_PATTERN=*** re.IGNORECASE)

SKIP_KEYS = {
    'DEBUG', 'NODE_ENV', 'APP_NAME', 'APP_PORT', 'LOG_LEVEL',
    'DOMAIN', 'HOST', 'PORT', 'URL', 'BASE_URL',
    'BACKEND_URL', 'FRONTEND_URL', 'NEXT_PUBLIC_',
}


def read_env_file(path, label=""):
    secrets = []
    try:
        with open(path) as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip("'\"")
                if SECRET_PATTERN.search(key) and key not in SKIP_KEYS:
                    secrets.append({
                        "source": label or path,
                        "source_type": "env_file",
                        "line": lineno,
                        "key": key,
                        "value": value,
                        "value_length": len(value),
                        "looks_sensitive": len(value) > 5,
                    })
    except FileNotFoundError:
        print(f"  [NOT FOUND] {path}", file=sys.stderr)
    except PermissionError:
        print(f"  [PERMISSION] {path}", file=sys.stderr)
    return secrets


def read_bash_profile(host=None):
    secrets = []
    if host:
        cmd = f"ssh -o ConnectTimeout=10 {host} 'cat ~/.bash_profile 2>/dev/null'"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            lines = result.stdout.strip().split('\n')
        except:
            return [{"source": f"{host}:~/.bash_profile", "error": "SSH failed"}]
    else:
        path = os.path.expanduser('~/.bash_profile')
        return read_env_file(path, "local:~/.bash_profile")
    for line in lines:
        line = line.strip()
        if 'export ' in line or 'export=' in line:
            m = re.match(r'export\s+(\w+)=(.*)', line)
            if m:
                key = m.group(1)
                value = m.group(2).strip().strip("'\"")
                if SECRET_PATTERN.search(key):
                    secrets.append({
                        "source": f"{host}:~/.bash_profile" if host else "~/.bash_profile",
                        "source_type": "bash_profile",
                        "key": key,
                        "value": value,
                        "value_length": len(value),
                        "looks_sensitive": len(value) > 5,
                    })
    return secrets


def github_secrets_list(repo_path):
    secrets = []
    for level in ['repo', 'environment', 'organization']:
        try:
            result = subprocess.run(
                f'cd {repo_path} && gh secret list --{level} --json name,type,updatedAt',
                shell=True, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for s in data:
                    secrets.append({
                        "source": f"{repo_path} ({level})",
                        "source_type": "github_secret",
                        "key": s.get("name", ""),
                        "type": s.get("type", ""),
                        "updated": s.get("updatedAt", ""),
                        "value": "[GitHub secret - value not exposed]",
                    })
        except Exception as e:
            print(f"  [GH ERROR] {repo_path} ({level}): {e}", file=sys.stderr)
    return secrets


def main():
    parser = argparse.ArgumentParser(description="Scan for secrets in env files")
    parser.add_argument('--env-path', help='Path to a single .env file to scan')
    parser.add_argument('--all-repos', action='store_true', help='Scan all known repos')
    parser.add_argument('--vm-host', help='Remote VM host for ~/.bash_profile scan')
    parser.add_argument('--list-directories', action='store_true', help='List known env file locations')
    parser.add_argument('--output', help='Output file (default: stdout)')
    args = parser.parse_args()

    known_dirs = [
        '/Users/manjunathkanavi/.hermes/git_clone_dir/iacgenie',
        '/Users/manjunathkanavi/.hermes/git_clone_dir/LightSerp',
        '/Users/manjunathkanavi/workspace/git_workspace/iacgenie-unified-infra',
        '/Users/manjunathkanavi/workspace/git_workspace/LightSerp',
        '/Users/manjunathkanavi/workspace/git_workspace/terragenius',
        '/Users/manjunathkanavi/.hermes/git_clone_dir/Hisaab',
    ]

    if args.list_directories:
        for d in known_dirs:
            found = []
            for root, dirs, files in os.walk(d):
                for f in files:
                    if f.startswith('.env') or f == '.env':
                        found.append(os.path.join(root, f))
            print(f"{d}:")
            for f in found:
                print(f"  {f}")
            if not found:
                print("  (no .env files found)")
            print()
        return

    catalog = {"scanned_at": datetime.utcnow().isoformat(), "sources": []}

    if args.env_path:
        cat = read_env_file(args.env_path)
        catalog["sources"].extend(cat)
    elif args.all_repos or not args.env_path:
        for d in known_dirs:
            if not os.path.isdir(d):
                continue
            for root, dirs, files in os.walk(d):
                for f in files:
                    if f.startswith('.env') or f == '.env':
                        fpath = os.path.join(root, f)
                        rel = os.path.relpath(fpath, d)
                        cat = read_env_file(fpath, f"{d}/{rel}")
                        catalog["sources"].extend(cat)
            cat = github_secrets_list(d)
            catalog["sources"].extend(cat)
        if args.vm_host:
            cat = read_bash_profile(args.vm_host)
            catalog["sources"].extend(cat)
    else:
        print("Specify --env-path or --all-repos", file=sys.stderr)
        sys.exit(1)

    total = len(catalog["sources"])
    sensitive = sum(1 for s in catalog["sources"] if s.get("looks_sensitive"))
    catalog["summary"] = {
        "total_secrets_found": total,
        "potentially_sensitive": sensitive,
        "unique_keys": len(set(s["key"] for s in catalog["sources"])),
    }

    output = json.dumps(catalog, indent=2)
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Catalog written to {args.output}")
    else:
        print(output)

    print(f"\n[Summary] Total: {total}, Sensitive: {sensitive}, Unique keys: {catalog['summary']['unique_keys']}", file=sys.stderr)


if __name__ == "__main__":
    main()
