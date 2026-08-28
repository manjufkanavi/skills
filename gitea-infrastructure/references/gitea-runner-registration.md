# Gitea Actions Runner Registration — Full Workflow

## Problem
Gitea runner binary (`gitea-runner` / `act_runner`) shows `unregistered runner` errors and cannot fetch jobs. The `.runner` config file exists but the token is stale/expired.

## Diagnosis
1. Check runner status: `sudo systemctl status gitea-runner`
2. Check runner logs: `journalctl -u gitea-runner --no-pager -n 20`
3. Verify `.runner` config: `cat /home/mkanavi/.runner`
4. Check if Gitea Actions is enabled: `docker exec -u 1000 gitea gitea actions --help`

## Root Causes

### 1. Token mismatch
The token in `.runner` no longer matches what Gitea has in its `action_runner_token` table. This happens when:
- The runner was deleted from Gitea but `.runner` still exists
- The token was rotated but the runner config wasn't updated
- The runner binary was reinstalled and got a new config

### 2. Gitea `change-password` gate
After `docker exec -u 1000 gitea gitea admin user change-password`, the web UI forces a password change. This blocks all admin pages (including Actions runner registration) until the gate is cleared.

### 3. Runner config path mismatch
The runner reads from `~/.runner` by default. Make sure this path is correct for the systemd service's `WorkingDirectory`.

## Fix: Full Regeneration

### Step 1: Generate a fresh token
```bash
docker exec -u 1000 iacgenie-gitea gitea actions generate-runner-token
```
Output: a single token string (e.g., `mOGYuiXLtLYs0ejLSAZOFahrVx51z24iaXxoGGG4`)

### Step 2: Register the runner
```bash
cd /home/mkanavi
/home/mkanavi/bin/gitea-runner register \
  -c /home/mkanavi/.runner \
  --token <TOKEN> \
  --name iacgenie-vm-runner \
  --instance http://127.0.0.1:3000 \
  --no-interactive \
  --labels 'ubuntu-latest:docker://docker.gitea.com/runner-images:ubuntu-latest,ubuntu-24.04:docker://docker.gitea.com/runner-images:ubuntu-24.04'
```

### Step 3: Restart the service
```bash
sudo systemctl restart gitea-runner
sudo systemctl status gitea-runner --no-pager
```

### Step 4: Verify
```bash
journalctl -u gitea-runner --no-pager -n 5
# Should show: "runner: iacgenie-vm-runner, with version: v0.6.1, with labels: [ubuntu-latest ubuntu-24.04], declare successfully"
```

## Token Rotation (periodic)
```bash
sudo systemctl stop gitea-runner
rm -f /home/mkanavi/.runner
TOKEN=$(docker exec -u 1000 iacgenie-gitea gitea actions generate-runner-token)
cd /home/mkanavi
/home/mkanavi/bin/gitea-runner register -c /home/mkanavi/.runner --token "$TOKEN" --instance http://127.0.0.1:3000 --no-interactive
sudo systemctl start gitea-runner
journalctl -u gitea-runner --no-pager -n 5
```

## Reference
- Gitea Actions runner: https://gitea.com/gitea/act_runner
- Runner binary: `https://dl.gitea.com/act_runner/<version>/act_runner-<version>-linux-amd64`
- `gitea-runner register --help` for available flags
- `gitea actions generate-runner-token --help` for token generation
