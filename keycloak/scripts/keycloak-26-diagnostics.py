#!/usr/bin/env python3
"""
Keycloak 26.x Diagnostics Script
Rapid health check for Keycloak installations in Docker Compose.

Usage:
  python3 keycloak-diagnostics.py                  # Defaults to 127.0.0.1:8083
  python3 keycloak-diagnostics.py --port 8080      # Direct container port
  python3 keycloak-diagnostics.py --port 8083 --token <ADMIN_TOKEN>

Output: structured JSON + human-readable summary.
"""

import argparse
import json
import sys
import subprocess
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def check_port(host, port):
    try:
        result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and host in line:
                return True, line.strip()
        return False, "Not found"
    except Exception as e:
        return False, str(e)


def http_check(url):
    try:
        req = Request(url)
        resp = urlopen(req, timeout=10)
        body = resp.read(500).decode("utf-8", errors="replace")
        return True, resp.status, body[:200]
    except HTTPError as e:
        body = e.read(200).decode("utf-8", errors="replace") if e.fp else ""
        return False, e.code, body[:200]
    except URLError as e:
        return False, 0, str(e.reason)


def docker_check(container_name="iacgenie_keycloak"):
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}",
             "--format", "{{.Names}}|{{.Status}}|{{.Ports}}"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split("|")
            return {
                "container": parts[0],
                "status": parts[1] if len(parts) > 1 else "unknown",
                "ports": parts[2] if len(parts) > 2 else "unknown",
                "running": True
            }
        return {"error": "Container not found or not running"}
    except Exception as e:
        return {"error": str(e)}


def get_realm_info(host, port):
    url = f"http://{host}:{port}/realms/master"
    ok, code, body = http_check(url)
    if ok and code == 200:
        try:
            data = json.loads(body)
            return {
                "realm": data.get("realm"),
                "enabled": data.get("enabled"),
                "display_name": data.get("displayName", "N/A"),
                "public_key_prefix": data.get("public_key", "")[:20]
            }
        except json.JSONDecodeError:
            return {"error": "Not valid JSON", "raw_snippet": body[:100]}
    return {"error": f"HTTP {code}", "reachable": ok}


def main():
    parser = argparse.ArgumentParser(description="Keycloak 26.x Diagnostics")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="8083")
    args = parser.parse_args()

    host, port = args.host, args.port
    print("=" * 60)
    print(f"Keycloak Diagnostics — {host}:{port}")
    print("=" * 60)

    results = {}

    print("\n[1] Docker Container")
    dc = docker_check()
    print(f"  Status: {dc.get('status', 'N/A')}")
    print(f"  Ports:  {dc.get('ports', 'N/A')}")
    results["docker"] = dc

    print("\n[2] Port Listening")
    port_ok, port_info = check_port(host, port)
    print(f"  Port {port}: {'LISTENING' if port_ok else 'NOT LISTENING'}")
    results["port"] = {"listening": port_ok, "detail": port_info}

    print("\n[3] HTTP Endpoints")
    for path in ["/realms/master", "/admin/realms/master"]:
        url = f"http://{host}:{port}{path}"
        ok, code, body = http_check(url)
        status = "OK" if ok else f"FAIL ({code})"
        print(f"  {path:30s} {status}")
        results[path] = {"status": code, "reachable": ok}

    print("\n[4] Realm Info")
    realm = get_realm_info(host, port)
    print(f"  Realm: {realm.get('realm', 'unknown')}")
    print(f"  Enabled: {realm.get('enabled', 'N/A')}")
    results["realm"] = realm

    all_ok = port_ok and results.get("/realms/master", {}).get("reachable")
    print("\n" + "=" * 60)
    print(f"Overall: {'HEALTHY' if all_ok else 'DEGRADED'}")
    print("=" * 60)
    print("\n--- JSON ---")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
