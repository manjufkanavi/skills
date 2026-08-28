# Kanban Task Body Template — Infrastructure Tasks

Use this template when creating kanban tasks for infrastructure work.
Ensures every task has verification gates and mandatory rules.

## Template

```
**Goal:** [One-line description of what the task achieves]

**Steps:**
1. [Action step 1]
2. [Action step 2]
3. [Action step 3]
4. [Action step 4]
5. [Action step 5]

**MANDATORY RULE: After making changes:**
1. Deploy and verify the service — SSH to VM, run ansible-playbook, verify service works
2. Document changes in INFRA-DESIGN.md
3. Commit and push changes to git with descriptive message
4. Verify: [specific verification command or check]

**Files to modify:**
- [path/to/file1]
- [path/to/file2]
```

## Example

```
**Goal:** Enable TLS on OpenBao listener so all secret traffic is encrypted.

**Steps:**
1. Generate self-signed TLS cert for OpenBao (CN=openbao.local, SAN=127.0.0.1)
2. Update roles/openbao/templates/openbao-prod.hcl.j2 to use TLS listener
3. Copy cert files into roles/openbao/files/ directory
4. Update docker-compose template to mount cert volumes
5. Update all Python scripts to use HTTPS with proper cert verification

**MANDATORY RULE: After making changes:**
1. Deploy and verify the service — SSH to VM, run ansible-playbook, verify OpenBao responds on HTTPS
2. Document changes in INFRA-DESIGN.md
3. Commit and push changes to git with descriptive message
4. Verify: curl -k https://127.0.0.1:8200/v1/sys/health returns 200

**Files to modify:**
- roles/openbao/templates/openbao-prod.hcl.j2
- roles/openbao/files/ (cert files)
- docker-compose.yml.j2 (volume mounts)
```

## When to Use

- Every infrastructure kanban task
- Every task that modifies deployed services
- Every task that changes configuration files
- Every task that affects production state

## When NOT to Use

- Simple documentation-only tasks (still needs verification, but can be shorter)
- Research/planning tasks (use a different body format)
- One-off cleanup tasks (can be shorter)
