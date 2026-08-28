#!/usr/bin/env python3
"""
Provision Keycloak realm and OIDC clients using Admin REST API.

Bypasses kcadm.sh stdin bug in Keycloak 26 by using Python urllib directly.

Usage:
    python3 keycloak-provision.py \
        --kc-url http://127.0.0.1:8083 \
        --realm iacgenie \
        --admin-user admin \
        --admin-pass Kc8xL2mNp9Qr4vWy7zBf3jHa5dGe6tRu

Optional files (read if present):
    /tmp/clients.json - Clients to create (overrides --clients flag)

Defaults:
    - Creates realm 'iacgenie' with typical settings
    - Creates 6 clients: admin-service, auth-wrapper, clamav-wrapper,
      crowdsec-wrapper, pagegen-wrapper, gitea
    - Creates admin user if missing
"""
import argparse, json, sys, urllib.request, urllib.parse, hashlib

DEFAULT_CLIENTS = [
    {
        "clientId": "admin-service",
        "name": "IacGenie Admin Service",
        "redirectUris": [
            "https://auth.iacgenie.com/*",
            "https://gitea.iacgenie.com/*",
            "https://vault.iacgenie.com/*",
        ],
        "clientSecret": "admin-svc-secret-admin1234567890",
    },
    {
        "clientId": "auth-wrapper",
        "name": "Shared Auth Wrapper",
        "redirectUris": [
            "https://clamav.iacgenie.com/*",
            "https://crowdsec.iacgenie.com/*",
            "https://pagegen.iacgenie.com/*",
        ],
        "clientSecret": "auth-wr-secret-authwrapper123",
    },
    {
        "clientId": "clamav-wrapper",
        "name": "ClamAV Dashboard",
        "redirectUris": [
            "https://clamav.iacgenie.com/*",
            "https://auth.iacgenie.com/*",
        ],
        "clientSecret": "clamav-secret-clamav123456789",
    },
    {
        "clientId": "crowdsec-wrapper",
        "name": "CrowdSec Dashboard",
        "redirectUris": [
            "https://crowdsec.iacgenie.com/*",
            "https://auth.iacgenie.com/*",
        ],
        "clientSecret": "crowdsec-secret-crowdsec12345",
    },
    {
        "clientId": "pagegen-wrapper",
        "name": "PageGen Dashboard",
        "redirectUris": [
            "https://pagegen.iacgenie.com/*",
            "https://auth.iacgenie.com/*",
        ],
        "clientSecret": "pagegen-secret-pagegen1234567",
    },
    {
        "clientId": "gitea",
        "name": "Gitea Git Service",
        "redirectUris": ["https://gitea.iacgenie.com/user/oauth2/gitea"],
        "clientSecret": "gitea-secret-gitea1234567890",
    },
]


def get_token(kc_url, admin_user, admin_pass):
    """Get admin token from Keycloak OIDC endpoint."""
    data = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": admin_user,
            "password": admin_pass,
            "realm": "master",
        }
    ).encode()
    req = urllib.request.Request(
        kc_url + "/realms/master/protocol/openid-connect/token",
        data=data,
        method="POST",
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read())
            return d["access_token"]
    except urllib.error.HTTPError as e:
        print("ERROR: Could not get admin token: HTTP %d" % e.code)
        print("  Check: admin user, password, and Keycloak port are correct")
        sys.exit(1)


def api(kc_url, method, path, data=None, token=None):
    """Make API call to Keycloak Admin REST API."""
    token = token or get_token(args.kc_url, args.admin_user, args.admin_pass)
    url = kc_url + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 204:
                return None
            rd = resp.read()
            return json.loads(rd) if rd else None
    except urllib.error.HTTPError as e:
        bt = e.read().decode()
        if e.code == 409:
            return None  # Already exists
        if e.code == 404:
            return None
        print("  [ERR] HTTP %d: %s" % (e.code, bt[:200]))
        return None


def log(msg):
    print("  [OK] " + msg)


def create_realm(kc_url, realm_data):
    """Create realm if it doesn't exist."""
    realms = api(kc_url, "GET", "/admin/realms")
    if not realms:
        print("  [ERR] Could not list realms")
        sys.exit(1)

    for r in realms:
        if r.get("realm") == args.realm:
            log("Realm '%s' already exists" % args.realm)
            return

    # Try /admin/realms first, fall back to /realms
    result = api(kc_url, "POST", "/admin/realms", realm_data)
    if not result:
        result = api(kc_url, "POST", "/realms", realm_data)
    if result:
        log("Created realm '%s' (id: %s)" % (args.realm, result.get("id")))
    else:
        print("  [ERR] Failed to create realm")
        sys.exit(1)


def create_user(kc_url, realm, user_data):
    """Create admin user if missing."""
    users = api(kc_url, "GET", "/admin/realms/%s/users?username=%s" % (realm, user_data["username"]))
    if users and len(users) > 0:
        log("User '%s' already exists" % user_data["username"])
        return

    # Use curl for user creation (captures 201 HTTP code)
    import subprocess
    url = kc_url + "/admin/realms/%s/users" % realm
    cmd = [
        "curl", "-s", "-w", "\n%{http_code}",
        url, "-X", "POST",
        "-H", "Authorization: Bearer *** + get_token(args.kc_url, args.admin_user, args.admin_pass),
        "-H", "Content-Type: application/json",
        "-d", json.dumps(user_data),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    lines = r.stdout.strip().split("\n")
    http_code = lines[-1]
    if http_code == "201":
        log("Created user '%s'" % user_data["username"])
    else:
        print("  HTTP %s: %s" % (http_code, r.stdout[:200]))


def create_clients(kc_url, realm, clients):
    """Create OIDC clients if missing."""
    for client in clients:
        cid = client["clientId"]
        print("  Client: %s" % cid)

        existing = api(kc_url, "GET", "/admin/realms/%s/clients?clientId=%s" % (realm, cid))
        if existing and len(existing) > 0:
            log("Client '%s' already exists" % cid)
            continue

        cdata = {
            "clientId": cid,
            "name": client.get("name", cid),
            "enabled": True,
            "clientAuthenticatorType": "client-secret",
            "redirectUris": client.get("redirectUris", []),
            "webOrigins": ["+"],
            "protocol": "openid-connect",
            "standardFlowEnabled": True,
            "implicitFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "serviceAccountsEnabled": False,
            "publicClient": False,
            "frontchannelLogout": True,
            "consentRequired": False,
            "clientSecret": client.get("clientSecret", ""),
            "attributes": {
                "oauth2.device.authorization.grant.enabled": "false",
                "pkce.code.challenge.method.s256": "true",
            },
        }

        result = api(kc_url, "POST", "/admin/realms/%s/clients" % realm, cdata)
        if result:
            log("Created client '%s' (id: %s)" % (cid, result.get("id")))
        else:
            print("  [WARN] Failed to create client '%s'" % cid)


def main():
    global args
    parser = argparse.ArgumentParser(description="Provision Keycloak realm and clients")
    parser.add_argument("--kc-url", default="http://127.0.0.1:8083", help="Keycloak admin URL")
    parser.add_argument("--realm", default="iacgenie", help="Realm name to create")
    parser.add_argument("--admin-user", default="admin", help="Keycloak admin username")
    parser.add_argument("--admin-pass", required=True, help="Keycloak admin password")
    parser.add_argument("--clients-file", help="JSON file with clients to create")
    parser.add_argument("--create-realm", action="store_true", help="Also create the realm")
    parser.add_argument("--create-user", action="store_true", help="Also create admin user")
    parser.add_argument("--skip-users", action="store_true", help="Skip user creation")
    args = parser.parse_args()

    token = get_token(args.kc_url, args.admin_user, args.admin_pass)
    print("Token: %s... (%d chars)" % (token[:40], len(token)))

    # Load clients from file or use defaults
    if args.clients_file:
        with open(args.clients_file) as f:
            clients = json.load(f)
    else:
        clients = DEFAULT_CLIENTS

    # Step 1: Create realm
    if args.create_realm:
        print("\n=== Creating Realm ===")
        realm_data = {
            "name": args.realm,
            "enabled": True,
            "displayName": "IacGenie Platform",
            "accessTokenLifespan": 3600,
            "ssoSessionIdleTimeout": 43200,
            "sslRequired": "external",
            "registrationAllowed": False,
            "registrationEmailAsUsername": True,
            "passwordPolicy": "length=12 and notUsername and specialCharacters=2",
            "loginWithEmailAllowed": True,
            "resetPasswordAllowed": True,
        }
        create_realm(args.kc_url, realm_data)

    # Step 2: Create admin user
    if args.create_user and not args.skip_users:
        print("\n=== Creating Admin User ===")
        user_data = {
            "username": args.admin_user,
            "email": args.admin_user + "@" + args.realm + ".com",
            "firstName": "Platform",
            "lastName": "Admin",
            "emailVerified": True,
            "enabled": True,
            "credentials": [
                {
                    "type": "password",
                    "value": "IacGenie@2026!Admin",
                    "temporary": False,
                }
            ],
        }
        create_user(args.kc_url, args.realm, user_data)

    # Step 3: Create clients
    print("\n=== Creating OIDC Clients ===")
    create_clients(args.kc_url, args.realm, clients)

    # Summary
    print("\n" + "=" * 60)
    print("PROVISIONING COMPLETE")
    print("=" * 60)
    print("Realm:   %s" % args.realm)
    print("Admin:   %s / IacGenie@2026!Admin" % args.admin_user)
    print("Clients:")
    for c in clients:
        print("  %s: %s" % (c["clientId"], c.get("clientSecret", "N/A")))
    print("=" * 60)


if __name__ == "__main__":
    main()
