# Shell Escaping When Modifying Remote Config Files

## Problem

When modifying configuration files on remote VMs via SSH, shell variable expansion (`${VAR}`) in file content gets interpreted by the local shell before being sent to the remote host. This corrupts files containing nginx variables (`$host`, `$remote_addr`), docker-compose env vars (`${REDIS_PASSWORD}`), or any `${...}` patterns.

## Symptoms

- `sed -i "s/\${REDIS_PASSWORD}/CHANGE_ME/g" file` fails silently or corrupts the file
- Perl/awk commands with `${...}` patterns fail with syntax errors
- File content shows truncated or mangled variable references after modification

## Diagnosis

### Inspect exact bytes in the file
```bash
# Use od -c to see exact characters
ssh user@host "grep 'PATTERN' file | od -c | head -5"
# Shows: D=${RE...D} → actual content is ${REDIS_PASSWORD}

# Use cat -v to see special characters
ssh user@host "grep 'PATTERN' file | cat -v"

# Use xxd for hex dump
ssh user@host "grep 'PATTERN' file | xxd | head -10"
```

## Solutions (in order of reliability)

### 1. `echo` + `sed -i "/PATTERN/c\\$(cat /tmp/file)"` (Most Reliable)

```bash
# Step 1: Write the replacement line to a temp file
echo "      - QUEUE_BULL_REDIS_PASSWORD=*** > /tmp/redis_line.txt

# Step 2: Use sed's c\ command to replace the matching line
ssh user@host "sed -i \"/QUEUE_BULL_REDIS_PASSWORD/c\\\\\\$(cat /tmp/redis_line.txt)\" ~/docker/iacgenie/docker-compose.resume-platform.yml"

# Step 3: Verify
ssh user@host "grep 'QUEUE_BULL_REDIS_PASSWORD' ~/docker/iacgenie/docker-compose.resume-platform.yml"
```

**Why it works:** The `c\` command in sed replaces the entire matching line. By writing the replacement to a temp file first and using `$(cat /tmp/file)`, we avoid shell expansion issues with `${VAR}` patterns.

### 2. Single-Quoted SSH Commands

```bash
# Use single quotes around the entire SSH command to prevent local shell expansion
ssh user@host 'sed -i "s/\${REDIS_PASSWORD}/CHANGE_ME/g" file'
```

**Pitfall:** This often fails because the remote shell still interprets `$` in double-quoted sed expressions. Use single quotes for the sed expression too:
```bash
ssh user@host 'sed -i '"'"'s/\${REDIS_PASSWORD}/CHANGE_ME/g'"'"' file'
```

### 3. Write a Script to a File, Then Execute Remotely

```bash
# Write a Python script locally
cat > /tmp/fix_compose.py << 'PYEOF'
with open("/path/to/docker-compose.yml", "r") as f:
    content = f.read()
content = content.replace("${REDIS_PASSWORD}", "CHANGE_ME")
with open("/path/to/docker-compose.yml", "w") as f:
    f.write(content)
PYEOF

# SCP the script to the VM
scp /tmp/fix_compose.py user@host:/tmp/

# Execute on the VM
ssh user@host "python3 /tmp/fix_compose.py"
```

**Why this works:** The heredoc with quoted delimiter (`'PYEOF'`) prevents local shell expansion. The script is transferred as-is and executed on the remote host.

### 4. Use `base64` Encoding

```bash
# Encode the replacement string
REPLACEMENT=$(printf "CHANGE_ME" | base64)

# Decode on the remote host
ssh user@host "echo '$REPLACEMENT' | base64 -d"
```

## Prevention

### When sending commands to remote VMs:
- **Use single quotes** around the entire SSH command: `ssh user@host 'command with $variables'`
- **Use heredocs with quoted delimiter:** `ssh user@host 'cat > file << '\''EOF'\'' ... EOF'`
- **Write scripts to files first** (via `write_file` + `scp`), then execute remotely
- **Never use double quotes** for SSH commands containing `$` — the local shell will expand them

### When modifying docker-compose files:
- **Test the sed pattern locally first** before running on the remote host
- **Verify the file content after modification** using `grep` + `od -c` or `cat -v`
- **Recreate containers** after modifying docker-compose files — `docker restart` does NOT pick up new env vars

## Related Pitfalls

- **docker-compose variable expansion:** `${VAR}` in docker-compose files is expanded from `.env` files. If the `.env` file doesn't have the variable, the literal `${VAR}` string is used.
- **Nginx variables:** `$host`, `$remote_addr`, `$scheme` in nginx configs must NOT be escaped — they are nginx variables, not shell variables. Use single-quoted SSH commands.
- **Ansible templates:** Jinja2 variables (`{{ var }}`) in Ansible templates are expanded by Ansible, not by the shell. But when manually editing deployed files, be careful not to trigger shell expansion.