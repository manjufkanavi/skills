#!/usr/bin/env python3
"""OpenBao KV Verification — full traversal + cross-tenant isolation.

Usage: python3 verify-openbao-kv.py <token_file>
  Reads root token from file, verifies all KV secrets, tests cross-tenant isolation.

Requires: urllib.request (stdlib), json (stdlib)
"""
import urllib.request
import json
import sys
import os

with open(sys.argv[1]) as f:
    ROOT_TOKEN=*** = "http://127.0.0.1:8200/v1"
HEADERS = {"X-Vault-Token": ROOT_TOKEN, "Content-Type": "application/json"}


def get(path):
    """GET from OpenBao API, return parsed JSON or error dict."""
    try:
        req = urllib.request.Request(BASE + path, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": str(e.code), "errors": e.read().decode()}


def get_all_keys(prefix):
    """Recursively list ALL keys in a KV-v2 mount, handling pagination."""
    keys = []
    path = prefix + "/metadata/"
    while path:
        result = get(path)
        if "error" in result or "data" not in result:
            break
        data = result["data"]
        for k in data.get("keys", []):
            key = k.get("key", k)
            if key:
                keys.append(key)
        next_prefix = data.get("next_key")
        if next_prefix:
            path = next_prefix + "/metadata/"
        else:
            path = None
    return keys


def verify_secret(prefix, key, field):
    """Verify a specific secret field exists and returns a value."""
    result = get("%s/data/%s" % (prefix, key))
    if "data" in result and "data" in result["data"] and field in result["data"]["data"]:
        val = result["data"]["data"][field]
        if isinstance(val, str) and len(val) > 3:
            return True, val[:3] + "***" + val[-2:]
        return True, val
    return False, "MISSING"


def read_token_file(path):
    """Read a service token from its file."""
    with open(path) as f:
        return f.read().strip()


def main():
    # List all KV mounts
    mounts = get("/sys/mounts")
    kv_mounts = []
    for k, v in mounts.get("data", {}).items():
        if v.get("type") == "kv":
            kv_mounts.append(k.rstrip("/"))  # strip trailing slash

    print("=== KV Engine Inventory ===")
    for m in sorted(kv_mounts):
        keys = get_all_keys(m)
        print("  %s: %d secrets" % (m, len(keys)))

    # Known secret paths to verify
    checks = [
        ("iacgenie/kv", "postgres", "username"),
        ("iacgenie/kv", "redis", "host"),
        ("iacgenie/kv", "minio", "access_key"),
        ("iacgenie/kv", "keycloak", "admin_user"),
        ("iacgenie/kv", "gitea", "db_password"),
        ("iacgenie/kv", "searxng", "secret"),
        ("iacgenie/kv", "lightserp", "api_secret"),
        ("iacgenie/kv", "pagezen", "port"),
        ("iacgenie/kv", "nsqd", "data_path"),
        ("lightserp/kv", "postgres", "username"),
        ("lightserp/kv", "redis", "host"),
        ("lightserp/kv", "minio", "access_key"),
        ("lightserp/kv", "searxng", "secret"),
        ("lightserp/kv", "api", "api_secret"),
        ("terraform/kv", "postgres", "username"),
        ("terraform/kv", "openbao", "addr"),
    ]

    print("\n=== Secret Verification ===")
    ok = 0
    fail = 0
    for prefix, key, field in checks:
        exists, val = verify_secret(prefix, key, field)
        status = "OK" if exists else "MISS"
        print("  %s %s/%s (%s=%s)" % (status, prefix, key, field, val))
        if exists:
            ok += 1
        else:
            fail += 1

    # Cross-tenant isolation tests
    service_token_dir = "/home/mkanavi/docker/iacgenie/data/openbao_raft/service_tokens"
    if os.path.exists(service_token_dir):
        print("\n=== Cross-Tenant Isolation ===")
        tests = [
            ("lightserp_service", "iacgenie/kv/data/postgres", "LightSerp->IacGenie"),
            ("iacgenie_service", "lightserp/kv/data/api", "IacGenie->LightSerp"),
            ("iacgenie_service", "terraform/kv/data/postgres", "IacGenie->Terraform"),
            ("terraform_service", "iacgenie/kv/data/postgres", "Terraform->IacGenie"),
        ]

        for token_file, check_path, label in tests:
            token_path = os.path.join(service_token_dir, token_file + "_token.txt")
            if not os.path.exists(token_path):
                print("  SKIP %s (no token file)" % label)
                continue
            tok = read_token_file(token_path)
            req = urllib.request.Request(BASE + check_path, headers={"X-Vault-Token": tok})
            try:
                resp = urllib.request.urlopen(req, timeout=10)
                print("  FAIL %s: ACCESS (should be DENIED)" % label)
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    print("  PASS %s: DENIED (403)" % label)
                else:
                    print("  WARN %s: HTTP %d" % (label, e.code))
            except Exception as e:
                print("  ERR %s: %s" % (label, e))
    else:
        print("\n=== Isolation (skipped — no token dir) ===")

    print("\nResults: %d OK, %d MISSING out of %d checked" % (ok, fail, len(checks)))
