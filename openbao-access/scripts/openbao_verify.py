#!/usr/bin/env python3
"""Verify OpenBao secrets are readable with a given token.

Usage:
  python3 openbao_verify.py

Sets BAO_ADDR and BAO_TOKEN from ~/.bash_profile, then reads
key secrets from all three KV mounts to confirm access works.
"""
import subprocess, json, os

BAO = "/opt/homebrew/Cellar/openbao/2.6.1/bin/bao"

result = subprocess.run(
    ["bash", "-c", ". /Users/manjunathkanavi/.bash_profile 2>/dev/null; echo \"$OPENBAO_TOKEN\""],
    capture_output=True, text=True
)
root = result.stdout.strip()
if not root:
    print("ERROR: No OPENBAO_TOKEN found in ~/.bash_profile")
    exit(1)

env = {"BAO_ADDR": "https://vault.iacgenie.com", "BAO_TOKEN": root}

def run_bao(args):
    p = subprocess.Popen(
        [BAO] + args,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env
    )
    out, err = p.communicate()
    return out, err, p.returncode

checks = [
    ("iacgenie/kv", "services/iacgenie", "name"),
    ("iacgenie/kv", "services/postgres", "root_password"),
    ("iacgenie/kv", "services/redis", "password"),
    ("iacgenie/kv", "services/minio", "access_key"),
    ("iacgenie/kv", "services/keycloak", "admin_user"),
    ("iacgenie/kv", "services/keycloak", "admin_password"),
    ("iacgenie/kv", "services/gitea", "admin_user"),
    ("iacgenie/kv", "services/openbao", "root_token"),
    ("iacgenie/kv", "services/pagezen", "api_secret"),
    ("iacgenie/kv", "services/nsqd", "http_port"),
    ("lightserp/kv", "services/lightserp", "name"),
    ("lightserp/kv", "services/api", "api_secret"),
    ("lightserp/kv", "services/postgres", "username"),
    ("lightserp/kv", "services/redis", "password"),
    ("lightserp/kv", "services/minio", "access_key"),
    ("terraform/kv", "services/terragenius", "name"),
    ("terraform/kv", "services/openbao", "addr"),
    ("terraform/kv", "services/postgres", "password"),
]

print("=" * 60)
print("OpenBao Secret Verification")
print("=" * 60)

ok = 0
fail = 0
for mount, key, field in checks:
    out, err, rc = run_bao(["kv", "get", "-format=json", "-mount=" + mount, key])
    if rc == 0:
        d = json.loads(out)
        data = d.get("data", {}).get("data", {})
        if field in data:
            ok += 1
            val = data[field]
            if any(x in field.lower() for x in ("password", "secret", "key", "token")):
                print(f"  [OK] {mount}/{key}.{field} = *** ({len(val)} chars)")
            else:
                print(f"  [OK] {mount}/{key}.{field} = {val}")
        else:
            print(f"  [WARN] {mount}/{key}.{field} NOT FOUND")
            fail += 1
    else:
        print(f"  [ERR] {mount}/{key} read failed")
        fail += 1

print("\n" + "=" * 60)
print(f"Result: {ok} OK, {fail} issues")
if fail == 0:
    print("ALL CHECKS PASSED")
else:
    print(f"{fail} check(s) need attention")
print("=" * 60)
