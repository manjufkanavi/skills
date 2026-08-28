# OpenBao Policy Templates

## Global Admin Policy
# Grants full access to sys/ and root policies
```hcl
path "sys/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
path "auth/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
path "sys/mounts" {
  capabilities = ["read", "list"]
}
path "sys/policies/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
```

## Project-Specific KV Policy Template
# Adjust {project} and {prefix} as needed

```hcl
# Full CRUD + list on the project's KV mount
path "{prefix}/kv/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Read only (read-only consumers)
# path "{prefix}/kv/*" {
#   capabilities = ["read", "list"]
# }

# Metadata-only (audit/review)
# path "{prefix}/kv/metadata/*" {
#   capabilities = ["read", "list"]
# }
```

## Read-Only Consumer Policy
```hcl
path "{prefix}/kv/*" {
  capabilities = ["read", "list"]
}
```

## Backup Operator Policy
```hcl
path "sys/storage/raft/snapshot" {
  capabilities = ["read"]
}
path "sys/storage/raft/restore" {
  capabilities = ["update"]
}
path "sys/audit" {
  capabilities = ["read", "list"]
}
path "sys/seal-status" {
  capabilities = ["read"]
}
```

## AppRole Role Mapping
# When creating approle roles, assign the project-specific policy:
```bash
openbao write auth/approle/role/{project}-service \
  role_id="{project}-role-id" \
  secret_id_ttl="0" \
  token_ttl="1h" \
  token_max_ttl="4h" \
  policies="{project}-policy" \
  bound_cidr="10.0.0.0/8"
```

## Password Policy Template
# For userpass auth:
```hcl
min_length = 16
upper = 2
lower = 2
number = 2
special = 2
```
