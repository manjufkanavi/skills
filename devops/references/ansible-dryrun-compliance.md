# Ansible --check Mode Compliance Pitfalls

## The Core Problem

Ansible's `--check` (dry-run) mode still renders **all Jinja2 templates** even when tasks are skipped. This causes failures when:

1. `env.VAR` lookups reference environment variables that exist locally but NOT on the remote host
2. `register` variables from tasks with `when:` conditions aren't available when the template is rendered
3. `uri` module JSON body responses aren't parsed into `.json` attributes

## Pitfall 1: `env.VAR` Lookups in Role Defaults

**Wrong** (works on VM but fails in `--check`):
```yaml
my_secret: "{{ env.OPENBAO_ROOT_TOKEN | default('CHANGE_ME') }}"
```

**Why it fails:** `env.VAR` looks for the variable on the **remote host's** environment, not the ansible controller's. In `--check` mode, the variable doesn't exist on the VM.

**Correct** (accept extra-vars OR env vars):
```yaml
# defaults/main.yml — direct variable name, no env lookup
my_secret: "{{ my_secret | default('CHANGE_ME') }}"
# Pass via command line: ansible-playbook -e my_secret='<actual_value>' playbook.yml
```

Group vars still work because ansible reads them on the controller before deploying to the remote host. Ansible Vault variables (`inventory/group_vars/all.yml` encrypted) are decrypted on the controller, so they're available as direct variable names.

## Pitfall 2: `register` Variables with Conditional Tasks

**Wrong** (template renders before task runs in `--check`):
```yaml
- name: Get auth token
  uri:
    url: "http://localhost:8080/token"
  register: token_response
  when: some_condition

- name: Set token
  set_fact:
    token: "{{ token_response.json.access_token }}"
  when: some_condition
```

**Fix:** Add `ignore_errors: true` and `run_once: true` to the register task. Or use `lookup('env', 'VAR')` instead of uri response.

## Pitfall 3: `uri` Module JSON Response Parsing

**Wrong** (`.json` attribute doesn't exist on uri result):
```yaml
- name: Login
  uri:
    url: "http://localhost:8080/login"
    body_format: urlencoded
    return_contents: yes
  register: login_result

- name: Extract token
  set_fact:
    token: "{{ login_result.json.access_token }}"
```

**Correct** (parse `body` field with `from_json`):
```yaml
- name: Extract token
  set_fact:
    token: "{{ (login_result.body | from_json).access_token }}"
```

## Pitfall 4: Dict Key Access with Dot Notation

**Wrong** (bracket notation fails in `--check`):
```yaml
changed_when: my_var.status in [200, 201]
```

**Correct** (use bracket notation with `default` fallback):
```yaml
changed_when: my_var['status'] | default(409) in [200, 201]
```

## Pitfall 5: Missing Variable Defaults in Templates

**Wrong** (template references undefined variable):
```yaml
command: >
  docker exec postgres psql -c
  "SELECT r.id FROM repository r WHERE r.name = '{{ item.name }}'"
loop: "{{ mirror_repos }}"
```

If `mirror_repos` is a list of strings (not dicts with `name`), `item.name` fails.

**Correct** (loop over strings, reference `item` directly):
```yaml
- name: Deploy mirror
  command: >-
    docker exec postgres psql -c
    "SELECT r.id FROM repository r WHERE r.name = '{{ item }}'"
  loop: "{{ mirror_repos | default([]) }}"
  loop_control:
    label: "{{ item }}"
  when:
    - mirror_repos | default([]) | length > 0
    - some_other_required_var | default('') | length > 0
```

## Quick Checklist for Dry-Run Compliance

- [ ] No `env.VAR` lookups in role defaults — use direct variable names + `default()`
- [ ] `uri` module results: use `body | from_json`, not `.json` attribute
- [ ] Dict attributes: use `['key']` notation + `| default()` fallback
- [ ] `register` variables: add `ignore_errors: true` and `failed_when: false`
- [ ] All `when:` conditions: guard referenced variables with `| default()`
- [ ] All `loop:` variables: add `| default([])` for empty list safety
- [ ] All Jinja2 template variables: check for `undefined` in template rendering

## Debugging Dry-Run Failures

1. Read the ERROR traceback — it shows the exact template line
2. The `Origin:` line shows the file and line number
3. Look for `is undefined` — that variable needs a `| default()` guard
4. Look for `object of type 'dict' has no attribute` — needs bracket notation
5. Check if the variable comes from a `register` with `when:` — needs `ignore_errors`
