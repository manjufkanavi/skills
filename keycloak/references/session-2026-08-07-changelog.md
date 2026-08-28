This session produced concrete lessons about **Keycloak 26 credential table internals** (the multi-column schema, the `priority`/`secret_data` NULL pitfalls, the `kc.sh` networking trap) that weren't covered in the existing skill. A new `references/keycloak-26-credential-recovery.md` was added with:

1. **Credential table schema** — all 9 columns, types, nullable constraints
2. **Critical NULL constraints** — `priority` (primitive int) and `secret_data` (called `.replace()` on it) must never be NULL  
3. **salt column gotcha** — Keycloak reads raw bytes from `salt` (bytea), not from the base64 string in `credential_data.salt`
4. **SQL recipes** — updating a credential, generating PBKDF2-SHA256 hash in Python, deleting a credential
5. **kc.sh networking trap** — `kc.sh import` and `kc.sh bootstrap-admin` start their own Keycloak instance that can't reach Docker network services
6. **`--import-realm` vs `kc.sh import` comparison table**
7. **Admin login failure checklist** (8-step diagnostic)
8. **KC 26 admin redirect behavior**

Patches to SKILL.md: added NULL-constraint warnings to bootstrap-admin section, added kc.sh networking gotcha before the "Admin password does NOT update" section, added "See also" pointer to new reference.
