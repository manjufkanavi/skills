# Full admin policy for OpenBao admin user (userpass alias: admin)
# Grants full access to all namespaces, auth methods, and system operations

# Identity management — required for UI "Access" page
path "identity/*"                     { capabilities = ["create", "read", "update", "delete", "list", "sudo"] }
path "identity/group/*"               { capabilities = ["create", "read", "update", "delete", "list"] }
path "identity/alias/*"               { capabilities = ["create", "read", "update", "delete", "list"] }
path "identity/oidc/*"                { capabilities = ["read", "list"] }

# Secrets access
path "secret/*"                       { capabilities = ["create", "read", "update", "delete", "list"] }
path "secret"                         { capabilities = ["list"] }
path "iacgenie/kv/*"                  { capabilities = ["create", "read", "update", "delete", "list"] }
path "iacgenie/kv"                    { capabilities = ["list"] }
path "lightserp/kv/*"                 { capabilities = ["create", "read", "update", "delete", "list"] }
path "lightserp/kv"                   { capabilities = ["list"] }
path "terraform/kv/*"                 { capabilities = ["create", "read", "update", "delete", "list"] }
path "terraform/kv"                   { capabilities = ["list"] }

# System operations (admin only)
path "sys/*"                          { capabilities = ["create", "read", "update", "delete", "list", "sudo"] }

# Auth management
path "auth/*"                         { capabilities = ["create", "read", "update", "delete", "list", "sudo"] }
path "auth/userpass/users/*"          { capabilities = ["create", "read", "update", "delete", "list"] }

# Policy management
path "sys/policy/*"                  { capabilities = ["create", "read", "update", "delete", "list"] }

# Namespace management
path "sys/namespaces/*"              { capabilities = ["create", "read", "update", "delete", "list"] }

# Audit management
path "sys/audit/*"                   { capabilities = ["create", "read", "update", "delete", "list"] }

# Replication/HA
path "sys/storage/raft/*"            { capabilities = ["read", "list"] }
