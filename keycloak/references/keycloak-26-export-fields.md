# Keycloak 26.0 Realm Export — Removed/Renamed Fields

Keycloak 26.0 realm import rejects fields valid in 25.x. Gathered Jul 28 2026 during IacGenie Phase 2.

## Removed Fields

| Field                          | Notes                                  |
|--------------------------------|----------------------------------------|
| `otpEnabled`                   | Replaced by `otpPolicyType`            |
| `otpRecoveryAuthnCodeFormat`   | N/A in 26                              |
| `otpPolicyCodeLength`          | Code length derived from policy        |

## Removed Wrappers

`realms` is no longer a top-level array. Import accepts **one realm at a time** at the top level. For multiple realms, use Admin REST API.

## Runtime Errors

```
ERROR: Unrecognized field "otpEnabled" (class RealmRepresentation)
ERROR: Unrecognized field "otpPolicyCodeLength" (class RealmRepresentation)
ERROR: Unrecognized field "realms" (class RealmRepresentation)
```

## Working Minimal Structure

```json
{
  "realm": "iacgenie",
  "displayName": "IacGenie Platform",
  "enabled": true,
  "accessTokenLifespan": 3600,
  "otpPolicyType": "totp",
  "otpPolicyAlgorithm": "HmacSHA1",
  "otpPolicyPeriod": 30,
  "users": [],
  "clients": [],
  "roles": {"realm": [{"name": "user"}]}
}
```

## Confirmed Supported Fields (from error messages)

`userFederationMappers, rememberMe, duplicateEmailsAllowed, adminEventsDetailsEnabled, users, clientOfflineSessionMaxLifespan, webAuthnPolicyRequireResidentKey, webAuthnPolicyPasswordlessAvoidSameAuthenticatorRegister, components, otpPolicyType, accessCodeLifespanUserAction, id, webAuthnPolicyAttestationConveyancePreference, enabledEventTypes, applications, webAuthnPolicyPasswordlessSignatureAlgorithms, eventsListeners, ssoSessionMaxLifespanRememberMe, defaultDefaultClientScopes, webAuthnPolicyPasswordlessCreateTimeout, clientOfflineSessionIdleTimeout, notBefore, publicKey, smtpServer, clientPolicies, resetPasswordAllowed, webAuthnPolicyAvoidSameAuthenticatorRegister, accessTokenLifespanForImplicitFlow, webAuthnPolicyPasswordlessUserVerificationRequirement, clientScopes, internationalizationEnabled, defaultRole, accessTokenLifespan, passwordCredentialGrantAllowed, federatedUsers, applicationScopeMappings`
