# Keycloak 26 kcadm.sh stdin Limitations

## CRITICAL: stdin completely broken for ALL write operations

In Keycloak 26 (Quarkus), `kcadm.sh` cannot read stdin for any write operation.

ALL of these FAIL with "unable to read contents from stream":
- kcadm.sh create realms -s name=iacgenie
- kcadm.sh create realms -f /tmp/realm.json
- kcadm.sh create realms -b '{"name":"iacgenie"}'
- kcadm.sh create clients -r iacgenie -s clientId=auth-wrapper
- kcadm.sh update clients -s name=new-name
- kcadm.sh delete clients -s clientId=old-name

Reading (get) still works:
- kcadm.sh get realms
- kcadm.sh get clients -r iacgenie -q client_id=auth-wrapper
- kcadm.sh config credentials --server ... --user ... --pass ...

Cause: Quarkus-style stdin handling in kcadm.sh drops the pipe when invoked via `docker exec bash -c` or SSH. The stdin is silently lost.

## WORKAROUND: Use Admin REST API directly

### Preferred: Python + urllib (no kcadm.sh dependency)

See references/keycloak-26-kcadm-stdin-broken.md for the full Python provisioning pattern.

### Quick curl approach

Get token from OIDC endpoint (replaces kcadm.sh get-token which does not exist in KC 26):
curl -s -X POST http://127.0.0.1:8083/realms/master/protocol/openid-connect/token
  -H "Content-Type: application/x-www-form-urlencoded"
  -d "grant_type=password&client_id=admin-cli&username=admin&password=YOUR_PASS&realm=master"

Extract token and use:
curl -s -X POST http://127.0.0.1:8083/admin/realms
  -H "Authorization: Bearer *** -H "Content-Type: application/json"
  -d '{"name":"iacgenie","enabled":true}'

### Realm import (initial setup only)

docker cp realm.json iacgenie_keycloak:/opt/keycloak/data/import/realm.json
docker exec iacgenie_keycloak kc.sh start --import-realm

## Commands Reference

| Command | Status |
|---------|--------|
| get realms/clients/users | works |
| config credentials | works |
| create/update/delete | BROKEN - stdin dropped |

## Key Point

In Keycloak 26, kcadm.sh create/update/delete is DEPRECATED for automation. Use the Admin REST API via curl or Python for all write operations. kcadm.sh get is fine for read operations.