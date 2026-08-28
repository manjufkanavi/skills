#!/usr/bin/env python3
"""Ensure Keycloak client exists. Uses admin-cli login + Admin REST API."""
import argparse, sys
import httpx


def ensure_client(kc_url, realm, admin_user, admin_pass, client_id, client_secret, redirect_uris):
    with httpx.Client(timeout=10) as c:
        resp = c.post(f"{kc_url}/protocol/openid-connect/token", data={"grant_type": "password", "client_id": "admin-cli", "username": admin_user, "password": admin_pass})
        if resp.status_code != 200:
            print(f"Failed to get admin token: {resp.status_code}"); return 1
        admin_token = resp.json()["access_token"]
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"}
    with httpx.Client(timeout=10) as c:
        resp = c.get(f"{kc_url}/admin/realms/{realm}/clients?search={client_id}", headers=headers)
        existing = next((cl for cl in resp.json() if cl["clientId"] == client_id), None)
        if existing:
            payload = {"clientId": client_id, "enabled": True, "clientAuthenticatorType": "client-secret", "redirectUris": redirect_uris, "secret": client_secret}
            resp = c.put(f"{kc_url}/admin/realms/{realm}/clients/{existing['id']}", headers=headers, json=payload)
        else:
            payload = {"clientId": client_id, "enabled": True, "clientAuthenticatorType": "client-secret", "redirectUris": redirect_uris, "protocol": "openid-connect", "standardFlowEnabled": True, "directAccessGrantsEnabled": True, "publicClient": False, "secret": client_secret}
            resp = c.post(f"{kc_url}/admin/realms/{realm}/clients", headers=headers, json=payload)
    print(f"{'Updated' if existing else 'Created'} client '{client_id}' -> {resp.status_code}")
    return resp.status_code


def main():
    p = argparse.ArgumentParser(description="Ensure Keycloak client"); p.add_argument("--kc-url", required=True); p.add_argument("--realm", default="iacgenie"); p.add_argument("--admin-user", required=True); p.add_argument("--admin-password", required=True); p.add_argument("--client-id", required=True); p.add_argument("--secret", required=True); p.add_argument("--redirect-uris", nargs="+", required=True); a = p.parse_args()
    code = ensure_client(a.kc_url, a.realm, a.admin_user, a.admin_password, a.client_id, a.secret, a.redirect_uris)
    sys.exit(0 if code in (200, 201) else 1)

if __name__ == "__main__":
    main()