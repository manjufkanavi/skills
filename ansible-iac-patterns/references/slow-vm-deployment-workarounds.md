# Slow VM Deployment Workarounds

**Context:** The iacgenie deployment VM at `192.168.0.118` has extremely slow network (~65KB/s, frequent SSH timeouts). All remote operations must be optimized for this constraint.

## Connection Settings
Always use these SSH options to avoid timeouts:
```bash
ssh -o ConnectTimeout=30 -o ServerAliveInterval=5 mkanavi@192.168.0.118
```

## SCP vs Inline Python for File Updates
**Problem:** `scp` is too slow for large files or multiple files. **Solution:** Use inline Python heredoc via SSH exec to write/modify files directly on the VM.

```bash
ssh -o ConnectTimeout=30 mkanavi@192.168.0.118 "python3 << 'PYEOF'
import pathlib

p = pathlib.Path('/path/to/file')
content = p.read_text()
# ... modify content ...
p.write_text(content)
print('OK')
PYEOF"
```

This avoids network transfer entirely — the Python script runs on the VM. Use this for:
- Updating Jinja2 templates (nginx, compose)
- Modifying Ansible role files on the VM
- Any file modification that would otherwise require SCP

## Docker Builds on Slow Network
**Problem:** `docker build` fails with TLS handshake timeout when pulling images (Docker Hub not reachable via slow network).

**Solutions:**
1. **Use locally cached base images.** Check `docker images` before building to find available tags (e.g., `node:20-alpine` was cached but not `node:22-slim`).
2. **Build in background with timeout:** 
   ```bash
   ssh mkanavi@vm "cd /path && docker build -t tag . > /tmp/build.log 2>&1; echo DONE"
   ```

## File Ownership After Ansible Runs
Ansible creates files in `roles/*/templates/` as root. Any subsequent manual edit via SSH will fail with PermissionError:
```bash
# Fix before editing template files:
sudo chown mkanavi:mkanavi ~/iacgenie-platform/infra/ansible/roles/*/templates/*
```

## GitHub Auth Issues on VM
The VM's git remote may have expired PATs in the URL. If `git push` fails with "Authentication failed":
1. Check remote: `cd ~/repo && git remote -v`
2. Try SSH key if configured with proper permissions: `GIT_SSH_COMMAND='ssh -i ~/.ssh/github_sync' git push`
3. If no auth works, the commit is still saved locally — just needs manual intervention later
