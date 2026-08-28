#!/usr/bin/env python3
"""Verify a Keycloak admin password against the stored PBKDF2 hash in PostgreSQL.

Keycloak 26 uses PBKDF2-SHA256 (27500 iterations). The credential_data column
stores the hash info as JSON with base64-encoded salt and hash values.

Usage:
    python3 verify-kc-password.py <password>
    
Example:
    python3 verify-kc-password.py 'Kc8xL2mNp9Qr4vWy7zBf3jHa5dGe6tRu'
"""
import base64, hashlib, sys

def verify(passwords, salt_b64, stored_hash_b64):
    salt = base64.b64decode(salt_b64)
    for pw in passwords:
        h = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt, 27500, dklen=32)
        hash_b64 = base64.b64encode(h).decode()
        match = "MATCH!" if hash_b64 == stored_hash_b64 else "no match"
        print(f"  {pw:30s} → {hash_b64}  {match}")

if __name__ == "__main__":
    passwords = sys.argv[1:] if len(sys.argv) > 1 else [
        "Kc8xL2mNp9Qr4vWy7zBf3jHa5dGe6tRu",
        "KeycloakAdmin2026!",
        "changeme",
        "admin",
    ]
    
    print("Enter salt (base64 from credential_data.additionalParameters.salt):")
    salt_b64 = input().strip()
    print("Enter stored hash (base64 from credential_data.additionalParameters.value):")
    stored_hash_b64 = input().strip()
    
    print(f"\nVerifying against salt={salt_b64[:12]}... hash={stored_hash_b64[:12]}...\n")
    verify(passwords, salt_b64, stored_hash_b64)
