# OpenBao Antares Security Audit Pattern

## Context
When auditing an OpenBao deployment, collect state from the VM and send a structured prompt to a local LLM (antares-1b-mlx-8bit at `http://127.0.0.1:1234`) for a prioritized security report.

## Workflow

### Step 1: Collect State from VM
```bash
# OpenBao status and policies
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao bao status"
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao sh -c 'export BAO_SKIP_VERIFY=true && bao policy list'"
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao sh -c 'export BAO_SKIP_VERIFY=true && bao secrets list'"
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao sh -c 'export BAO_SKIP_VERIFY=true && bao auth list'"

# AppRole configs
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao sh -c 'export BAO_SKIP_VERIFY=true && bao read -format=json auth/approle/role/iacgenie-backend-svc'"

# Config files
ssh mkanavi@192.168.0.118 "cat /home/mkanavi/docker/iacgenie/data/openbao/openbao-prod.hcl"
ssh mkanavi@192.168.0.118 "cat /etc/nginx/conf.d/vault-iacgenie.conf"
ssh mkanavi@192.168.0.118 "cat /etc/cloudflared/config.yml | head -30"

# Docker security
ssh mkanavi@192.168.0.118 "grep -A5 security_opt /home/mkanavi/docker/iacgenie/docker-compose.yml | head -20"

# Internet reachability
curl -sk --connect-timeout 5 https://vault.iacgenie.com/v1/sys/health

# Cron
ssh mkanavi@192.168.0.118 "crontab -l"
```

### Step 2: Build Structured Prompt
Combine all output into a single markdown prompt with sections:
- OpenBao Status
- Policies
- Auth Methods
- Secret Engines
- AppRole Configs
- TLS Listener Config
- Listener Address
- Cron Jobs
- Backup Script Header
- Docker Security Settings
- Nginx Config
- Cloudflare Tunnel Config
- Internet Reachability

### Step 3: Send to Antares
```bash
curl -s http://127.0.0.1:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "antares-1b-mlx-8bit",
    "messages": [
      {"role": "system", "content": "You are a security auditor specializing in OpenBao/HashiCorp Vault deployments. Be thorough, factual, and prioritize by severity. Use structured output."},
      {"role": "user", "content": "<full prompt from Step 2>"}
    ],
    "temperature": 0.3,
    "max_tokens": 8000
  }'
```

### Step 4: Parse Results
The model returns findings in P0 (Critical), P1 (High), P2 (Medium), P3 (Low) categories with specific remediation steps.

## Common Findings to Expect

### P0 (Critical)
- TLS listener bound to `0.0.0.0` instead of `127.0.0.1`
- Missing TLS verification for local connections
- Overly permissive root token usage without policies

### P1 (High)
- `.env` files with world-readable permissions
- Missing audit logging
- No `cap_drop: ALL` on OpenBao container

### P2 (Medium)
- KV engines without explicit encryption at rest
- AppRole with long token TTLs
- No CIDR binding on AppRole

### P3 (Low)
- Single Raft node (no HA)
- Missing rate limiting on auth endpoints

## Example Output Format
```
| Severity | Finding | Recommendation |
|----------|---------|----------------|
| P0 | TLS listener bound to 0.0.0.0 | Change to 127.0.0.1 |
| P1 | .env world-readable | chmod 600 |
| P2 | No audit logging | Enable file-based audit |
```

## Tips
- Always read the token from `init_keys.json` at runtime, never hardcode in scripts
- Use `docker exec ... sh -c 'export BAO_SKIP_VERIFY=true'` for reliable `bao` CLI access
- The antares model is lightweight — set temperature low (0.3) for factual analysis
- Save results to `/tmp/openbao_security_audit_result.txt` for reference
- Anchor: openbao-security-audit
