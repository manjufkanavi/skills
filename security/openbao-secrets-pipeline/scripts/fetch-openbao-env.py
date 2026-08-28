#!/usr/bin/env python3
"""
Fetch all secrets from OpenBao KV and write unified .env file.
Designed to run on the VM where OpenBao is running.

Usage (on VM):
  python3 fetch-openbao-env.py
  # or via Ansible:
  # ansible.builtin.command: python3 /tmp/fetch-openbao-env.py

Outputs: /home/mkanavi/docker/iacgenie/.env
  - All KV values keyed as KVNAME_VALUEKEY (uppercase)
  - Postgres defaults injected if missing
  - LIGHTSERP_DATABASE_URL constructed from POSTGRES_USER/DB
"""
import json
import os
import subprocess
import sys

VAULT_ADDR = "http://127.0.0.1:8200"
ROOT_TOKEN_PATH = "/home/mkanavi/docker/iacgenie/data/openbao_raft/init_keys.json"
ENV_DEST = "/home/mkanavi/docker/iacgenie/.env"


def slurp(path):
    with open(path) as f:
        return json.load(f)


def openbao_get(path, token):
    r = subprocess.run(
        ["curl", "-sk", "-w", "\n%{http_code}", "-H", f"X-Vault-Token: {token}", f"{VAULT_ADDR}/v1/{path}"],
        capture_output=True, text=True,
    )
    lines = r.stdout.strip().split("\n")
    code = int(lines[-1])
    body = "\n".join(lines[:-1])
    return code, json.loads(body) if body else {}


def main():
    # 1. Read root token
    keys = slurp(ROOT_TOKEN_PATH)
    root = keys["root_token"]

    # 2. List KV keys
    code, data = openbao_get("iacgenie/kv/metadata/?list=true", root)
    if code != 200:
        print(f"ERROR: Could not list OpenBao KV secrets (HTTP {code})", file=sys.stderr)
        sys.exit(1)

    kv_keys = data.get("data", {}).get("keys", [])

    # 3. Read all secret values
    all_secrets = {}
    for k in kv_keys:
        code, data = openbao_get(f"iacgenie/kv/data/{k}", root)
        if code == 200:
            vals = data.get("data", {}).get("data", {})
            for vk, vv in vals.items():
                all_secrets[f"{k}_{vk}".upper()] = str(vv)

    # 4. Build unified env dict
    env = {"OPENBAO_ADDR": VAULT_ADDR}
    for k, v in all_secrets.items():
        env[k] = v

    # Inject defaults if KV didn't provide them
    env.setdefault("POSTGRES_USER", "iacgenie_pg")
    env.setdefault("POSTGRES_DB", "iacgenie")
    if "LIGHTSERP_DATABASE_URL" not in env:
        pg_user = env["POSTGRES_USER"]
        pg_db = env["POSTGRES_DB"]
        env["LIGHTSERP_DATABASE_URL"] = f"postgresql://{pg_user}:***@postgres:5432/{pg_db}"

    # 5. Write .env
    lines = [
        "# OpenBao-secrets-only environment",
        f"# Source: {VAULT_ADDR}",
        f"# Secrets count: {len(env)}",
        "",
    ]
    for k in sorted(env.keys()):
        lines.append(f"{k}={env[k]}")

    with open(ENV_DEST, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(ENV_DEST, 0o600)
    print(f"Written {len(env)} vars to {ENV_DEST}")


if __name__ == "__main__":
    main()
