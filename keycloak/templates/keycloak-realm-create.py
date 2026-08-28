#!/usr/bin/env python3
"""Create iacgenie realm in Keycloak and add admin user."""
import urllib.request
import urllib.parse
import json
import sys

KC_URL = "http://127.0.0.1:8083"
MASTER_USER = "admin"
MASTER_PASS = "CHANGE_ME"

def post_token(username, password):
    data = urllib.parse.urlencode({
        "grant_type": "password",
        "client_id": "admin-cli",
        "username": username,
        "password": password
    }).encode()
    req = urllib.request.Request(
        f"{KC_URL}/realms/master/protocol/openid-connect/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["access_token"]

def api(url, method="GET", data=None, token=None):
    hdrs = {"Content-Type": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        resp = urllib.request.urlopen(req)
        if resp.status in (201, 204):
            loc = resp.headers.get("Location", "")
            return loc.split("/")[-1] if loc else None
        raw = resp.read()
        return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        return {"error": str(e.code), "body": e.read().decode()[:300]}

def main():
    print("Getting master token...")
    token = post_token(MASTER_USER, MASTER_PASS)
    print(f"Token: {token[:25]}...")

    print("\n1. Creating iacgenie realm...")
    result = api(f"{KC_URL}/admin/realms", "POST", {
        "realm": "iacgenie",
        "enabled": True,
        "registrationAllowed": True,
        "resetPasswordAllowed": True,
        "loginWithEmailAllowed": True,
        "passwordPolicy": "length(8)"
    }, token)
    if result and "error" not in str(result):
        print(f"  Realm created: {result.get('realm', '?')}")
    else:
        print(f"  Result: {result}")

    print("\n2. Creating realm admin user...")
    user_id = api(f"{KC_URL}/admin/realms/iacgenie/users", "POST", {
        "username": "iacgenie-admin",
        "email": "admin@iacgenie.com",
        "enabled": True,
        "credentials": [{
            "type": "password",
            "value": "CHANGE_ME_PASSWORD",
            "temporary": False
        }]
    }, token)
    if user_id and "error" not in str(user_id):
        print(f"  User created: iacgenie-admin (id={user_id})")
    else:
        print(f"  Result: {user_id}")

    print("\n3. Listing realms...")
    realms = api(f"{KC_URL}/admin/realms", token=token)
    if realms and "error" not in str(realms):
        for r in realms:
            print(f"  realm={r.get('realm', r.get('name','?'))} enabled={r.get('enabled')}")

if __name__ == "__main__":
    main()
