# OpenBao Service Token Policies (HCL)
# Copy each block to a file and POST to sys/policies/acl/{name}

# ============================================
# DevOps Admin — full CRUD + system access
# ============================================
path "iacgenie/kv/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "lightserp/kv/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "terraform/kv/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "auth/*" {
  capabilities = ["read", "list"]
}
path "sys/*" {
  capabilities = ["read", "list"]
}

# ============================================
# Project Read-Only — read + list only
# ============================================
# Replace "PROJECT" with: iacgenie, lightserp, or terraform

path "PROJECT/kv/*" {
  capabilities = ["read", "list"]
}

# ============================================
# Service Read-Write — CRUD but no admin
# ============================================
# Use for CI/CD pipelines that need to rotate secrets

path "PROJECT/kv/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
