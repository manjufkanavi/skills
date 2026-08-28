# OpenBao Bootstrap Playbook Pattern

## Initialization (run once)

```yaml
# roles/openbao/tasks/init.yml
---
- name: Check if OpenBao is already initialized
  uri:
    url: "http://127.0.0.1:8200/v1/sys/init"
    method: GET
    status_code: [200, 400, 403, 503]
  register: init_check

- name: Initialize OpenBao (only if not initialized)
  block:
    - name: Initialize with Shamir keys
      uri:
        url: "http://127.0.0.1:8200/v1/sys/init"
        method: POST
        body_format: json
        body:
          secret_shares: "{{ openbao_secret_shares }}"
          secret_threshold: "{{ openbao_secret_threshold }}"
          root_token: "{{ openbao_root_token }}"
        status_code: 200
      register: init_result

    - name: Save initialization keys (chmod 600)
      copy:
        content: "{{ init_result.content }}"
        dest: "{{ openbao_raft_dir }}/init_keys.json"
        owner: "{{ deploy_user }}"
        group: "{{ deploy_user }}"
        mode: '0600'

  when:
    - "'initialized' not in init_check.json or not init_check.json.initialized"
```

## Unseal

```yaml
# roles/openbao/tasks/unseal.yml
---
- name: Read unseal keys from init result
  set_fact:
    unseal_keys: "{{ lookup('file', openbao_raft_dir + '/init_keys.json') | from_json }}"

- name: Apply first unseal key
  uri:
    url: "http://127.0.0.1:8200/v1/sys/unseal"
    method: POST
    body_format: json
    body:
      key: "{{ unseal_keys.unseal_keys_b64[0] }}"
    status_code: [200, 400]

- name: Apply second unseal key (threshold)
  uri:
    url: "http://127.0.0.1:8200/v1/sys/unseal"
    method: POST
    body_format: json
    body:
      key: "{{ unseal_keys.unseal_keys_b64[1] }}"
    status_code: [200, 400]
```

## Seeding (KV mounts, admin user, service tokens)

```yaml
# roles/openbao/tasks/seed.yml
---
- name: Enable KV-v2 at iacgenie/kv
  uri:
    url: "http://127.0.0.1:8200/v1/sys/mounts/iacgenie/kv"
    method: PUT
    body_format: json
    body:
      type: kv
      options:
        version: "2"
    status_code: [200, 409]

- name: Enable KV-v2 at lightserp/kv
  uri:
    url: "http://127.0.0.1:8200/v1/sys/mounts/lightserp/kv"
    method: PUT
    body_format: json
    body:
      type: kv
      options:
        version: "2"
    status_code: [200, 409]

- name: Enable KV-v2 at terraform/
  uri:
    url: "http://127.0.0.1:8200/v1/sys/mounts/terraform"
    method: PUT
    body_format: json
    body:
      type: kv
      options:
        version: "2"
    status_code: [200, 409]

- name: Create admin user
  uri:
    url: "http://127.0.0.1:8200/v1/auth/userpass/users/admin"
    method: POST
    body_format: json
    body:
      password: "{{ openbao_admin_password }}"
    status_code: [200, 400]

- name: Generate service tokens
  uri:
    url: "http://127.0.0.1:8200/v1/auth/token/create"
    method: POST
    body_format: json
    body:
      policies: ["{{ item.policy }}"]
      ttl: "{{ item.ttl }}"
    status_code: 200
  loop: "{{ openbao_service_tokens }}"
  loop_control:
    label: "{{ item.name }}"
  register: service_token_result
```

## Critical Pitfalls

- **OpenBao init is one-time only.** The init_keys.json must be preserved. If lost, you MUST wipe the Raft volume and re-initialize — no partial recovery.
- **Raft data persistence:** The `/openbao/raft` volume mount must survive container restarts. On VM reboot, Docker restarts the container but the volume persists.
- **Health check timing:** OpenBao needs `start_period: 30s` because init + unseal takes 10-30 seconds. The health check must wait for unseal.
- **Rate limiting:** Set `rate_limit = 0` in openbao-prod.hcl or health checks will be rate-limited and fail.
- **Audit logging:** File audit requires container restart with updated HCL config. Enable during initial bootstrap, not during routine deploys.