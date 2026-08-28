"""
Create Keycloak realms and clients via Admin REST API.
Works with Keycloak 26.x running in Docker Compose.

Usage:
  python3 create_kc_realms.py

Requires: .env file in the same directory with:
  KEYCLOAK_ADMIN=admin
  KEYCLOAK_ADMIN_PASSWORD=<your-pass>
  KC_BOOTSTRAP_ADMIN_PASSWORD=<your-pass>
"""

import requests, json, os, sys

# Read credentials from .env
env_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(env_dir, '.env')

if not os.path.exists(env_file):
    print("ERROR: .env file not found at " + env_file)
    sys.exit(1)

env = {}
with open(env_file) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            val = val.strip("'\"")
            env[key] = val

kc_admin = env.get('KC_BOOTSTRAP_ADMIN_USERNAME', env.get('KEYCLOAK_ADMIN', 'admin'))
kc_password = env.get('KC_BOOTSTRAP_ADMIN_PASSWORD', env.get('KEYCLOAK_ADMIN_PASSWORD'))
kc_port = env.get('KC_HTTP_PORT', '8080')

if not kc_password:
    print("ERROR: KC_BOOTSTRAP_ADMIN_PASSWORD (or KEYCLOAK_ADMIN_PASSWORD) not set in .env")
    sys.exit(1)

kc_url = "http://127.0.0.1:{}/realms/master/protocol/openid-connect/token".format(kc_port)
admin_base = "http://127.0.0.1:{}/admin/realms".format(kc_port)

# Get admin token
resp = requests.post(kc_url, data={
    'grant_type': 'password',
    'client_id': 'admin-cli',
    'username': kc_admin,
    'password': kc_password
})
if resp.status_code != 200:
    print("Failed to get admin token: {} - {}".format(resp.status_code, resp.text[:300]))
    sys.exit(1)

admin_token = resp.json()['access_token']
headers = {'Authorization': 'Bearer ' + admin_token, 'Content-Type': 'application/json'}

def post_realm(name, display_name):
    """Create a realm with basic config."""
    realm = {
        'realm': name,
        'displayName': display_name,
        'enabled': True,
        'accessTokenLifespan': 3600,
        'ssoSessionIdleTimeout': 1800,
        'ssoSessionMaxLifespan': 36000,
        'loginWithEmailAllowed': True,
        'duplicateEmailsAllowed': False,
        'resetPasswordAllowed': True,
        'registrationAllowed': True,
        'editUsernameAllowed': False,
        'rememberMe': True,
        'bruteForceProtected': True,
        'failureFactor': 10,
        'roles': {'realm': [{'name': 'user', 'description': 'Regular user'}]},
        'defaultRoles': ['user']
    }
    url = admin_base + '/master/realms'
    resp = requests.post(url, json=realm, headers=headers)
    if resp.status_code == 201:
        print("  Created realm: " + name)
        return name
    elif resp.status_code == 409:
        print("  Realm already exists: " + name)
        return name
    else:
        print("  ERROR creating realm {}: {} - {}".format(name, resp.status_code, resp.text[:200]))
        return None

def post_client(realm, client_config):
    """Create a client in a realm."""
    url = admin_base + '/' + realm + '/clients'
    resp = requests.post(url, json=client_config, headers=headers)
    if resp.status_code == 201:
        print("    Created client: " + client_config['clientId'])
        return resp.headers.get('Location', '').split('/')[-1]
    elif resp.status_code == 409:
        print("    Client already exists: " + client_config['clientId'])
        return None
    else:
        print("    ERROR creating client {}: {} - {}".format(client_config['clientId'], resp.status_code, resp.text[:200]))
        return None

# --- Main ---
print("Authenticating as {}...".format(kc_admin))
print("\nCreating realms...")

# Create iacgenie realm
print("\n[iacgenie realm]")
post_realm('iacgenie', 'IacGenie Platform')

# Create lightsrp realm
print("\n[lightsrp realm]")
post_realm('lightsrp', 'LightSerp')

# Create clients in iacgenie realm
print("\n[iacgenie clients]")
clients = [
    {
        'clientId': 'iacgenie-app',
        'name': 'IacGenie Application',
        'enabled': True,
        'clientAuthenticatorType': 'client-secret',
        'redirectUris': ['https://app.iacgenie.com/*', 'http://127.0.0.1:3070/*'],
        'webOrigins': ['+'],
        'protocol': 'openid-connect',
        'publicClient': False,
        'standardFlowEnabled': True,
        'implicitFlowEnabled': False,
        'directAccessGrantsEnabled': True,
        'serviceAccountsEnabled': False,
        'consentRequired': False,
        'attributes': {'oidc.ciba.grant.enabled': 'false'}
    },
    {
        'clientId': 'lightsrp-app',
        'name': 'LightSerp Application',
        'enabled': True,
        'clientAuthenticatorType': 'client-secret',
        'redirectUris': ['https://search.iacgenie.com/*', 'http://127.0.0.1:3070/*'],
        'webOrigins': ['+'],
        'protocol': 'openid-connect',
        'publicClient': False,
        'standardFlowEnabled': True,
        'implicitFlowEnabled': False,
        'directAccessGrantsEnabled': True,
        'serviceAccountsEnabled': False,
        'consentRequired': False,
        'attributes': {'oidc.ciba.grant.enabled': 'false'}
    },
    {
        'clientId': 'gitea-client',
        'name': 'Gitea OAuth',
        'enabled': True,
        'clientAuthenticatorType': 'client-secret',
        'redirectUris': ['https://gitea.iacgenie.com/*', 'http://127.0.0.1:3000/*'],
        'webOrigins': ['+'],
        'protocol': 'openid-connect',
        'publicClient': False,
        'standardFlowEnabled': True,
        'implicitFlowEnabled': False,
        'directAccessGrantsEnabled': True,
        'serviceAccountsEnabled': False,
        'consentRequired': False,
        'attributes': {'oidc.ciba.grant.enabled': 'false'}
    }
]

for c in clients:
    post_client('iacgenie', c)

# Create client in lightsrp realm
print("\n[lightsrp clients]")
post_client('lightsrp', {
    'clientId': 'lightsrp-webui',
    'name': 'LightSerp Web UI',
    'enabled': True,
    'clientAuthenticatorType': 'client-secret',
    'redirectUris': ['https://search.iacgenie.com/*', 'http://127.0.0.1:3070/*'],
    'webOrigins': ['+'],
    'protocol': 'openid-connect',
    'publicClient': False,
    'standardFlowEnabled': True,
    'implicitFlowEnabled': False,
    'directAccessGrantsEnabled': True,
    'serviceAccountsEnabled': False,
    'consentRequired': False,
    'attributes': {'oidc.ciba.grant.enabled': 'false'}
})

# List all realms
print("\n=== Keycloak Realms ===")
resp = requests.get(admin_base + '/master/realms', headers=headers)
for r in resp.json():
    if r['realm'] not in ('master',):
        print("  {} ({}) - enabled: {}".format(r['realm'], r['displayName'], r['enabled']))

print("\n=== DONE ===")
