"""
Quick diagnostics for Keycloak in Docker Compose.
Run from the docker/iacgenie/ directory (where .env lives).

Outputs: Keycloak health, DB connectivity, realm status, user status.

Usage:
  python3 keycloak-diagnostics.py
"""
import requests, subprocess, os, sys

env_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(env_dir, '.env')

env = {}
with open(env_file) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            val = val.strip("'\"")
            env[key] = val

kc_port = env.get('KC_HTTP_PORT', '8080')

def run(cmd):
    """Run a shell command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

print("=" * 50)
print("KEYCLOAK DIAGNOSTICS")
print("=" * 50)

# 1. Docker container status
print("\n[1] Container Status")
out, err, rc = run("docker ps --filter name=iacgenie-keycloak --format '{{.Status}} {{.Names}}'")
if out:
    print("  " + out)
else:
    print("  ERROR: Could not query container")

# 2. Keycloak health endpoint
print("\n[2] Health Endpoint")
try:
    resp = requests.get("http://127.0.0.1:{}/health/ready".format(kc_port), timeout=5)
    print("  Status: {} - {}".format(resp.status_code, resp.text[:100]))
except Exception as e:
    print("  Unreachable: " + str(e))

# 3. DB connectivity
print("\n[3] Postgres Connectivity")
out, err, rc = run("docker exec iacgenie-postgres psql -U keycloak -d keycloak -c 'SELECT 1' 2>&1")
if rc == 0:
    print("  OK: Can connect to postgres as keycloak")
else:
    print("  FAIL: " + out[:200] + err[:100])

# 4. Schema check
print("\n[4] Schema & Permissions")
out, err, rc = run("docker exec iacgenie-postgres psql -U postgres -d keycloak -c \"SELECT nspname, nspacl FROM pg_namespace WHERE nspname='public';\" 2>&1")
print("  " + out[:300] if out else "  ERROR: " + err[:200])

# 5. Search path
print("\n[5] Search Path")
out, err, rc = run("docker exec iacgenie-postgres psql -U keycloak -d keycloak -c 'SHOW search_path' 2>&1")
print("  " + out if out else "  ERROR: " + err[:200])

# 6. Master realm status
print("\n[6] Master Realm")
try:
    kc_admin = env.get('KC_BOOTSTRAP_ADMIN_USERNAME', env.get('KEYCLOAK_ADMIN', 'admin'))
    kc_pass = env.get('KC_BOOTSTRAP_ADMIN_PASSWORD', env.get('KEYCLOAK_ADMIN_PASSWORD'))
    if kc_pass:
        resp = requests.post(
            "http://127.0.0.1:{}/realms/master/protocol/openid-connect/token".format(kc_port),
            data={'grant_type': 'password', 'client_id': 'admin-cli', 'username': kc_admin, 'password': kc_pass},
            timeout=5
        )
        if resp.status_code == 200:
            token = resp.json()['access_token']
            headers = {'Authorization': 'Bearer ' + token}
            r = requests.get("http://127.0.0.1:{}/admin/realms/master".format(kc_port), headers=headers, timeout=5)
            if r.status_code == 200:
                realm = r.json()
                print("  Enabled: {}".format(realm.get('enabled')))
                print("  Users: {}".format(len(realm.get('users', []))))
                print("  Login allowed: {}".format(realm.get('loginAllowed', 'N/A')))
                for u in realm.get('users', []):
                    if u.get('username') in ('admin',):
                        print("  admin user enabled: {}".format(u.get('enabled')))
        else:
            print("  Token auth failed: {} - {}".format(resp.status_code, resp.text[:200]))
    else:
        print("  SKIPPED: No admin password in .env")
except Exception as e:
    print("  ERROR: " + str(e))

# 7. All realms
print("\n[7] All Realms")
try:
    if kc_pass:
        token = ''
        resp = requests.post(
            "http://127.0.0.1:{}/realms/master/protocol/openid-connect/token".format(kc_port),
            data={'grant_type': 'password', 'client_id': 'admin-cli', 'username': kc_admin, 'password': kc_pass},
            timeout=5
        )
        if resp.status_code == 200:
            token = resp.json()['access_token']
            headers = {'Authorization': 'Bearer ' + token}
            r = requests.get("http://127.0.0.1:{}/admin/realms/master/realms".format(kc_port), headers=headers, timeout=5)
            if r.status_code == 200:
                for realm in r.json():
                    print("  {} ({}) - enabled: {}".format(realm['realm'], realm.get('displayName', ''), realm.get('enabled')))
except Exception as e:
    print("  ERROR: " + str(e))

print("\n" + "=" * 50)
print("DIAGNOSTICS COMPLETE")
print("=" * 50)
