# Docker Bridge Network Recovery

## Problem

After a VM reboot, Docker fails to start with:

```
failed to start daemon: Error initializing network controller: error creating default "bridge" network: all predefined address pools have been fully subnetted
```

## Root Cause

The Docker daemon's default bridge network (`172.17.0.0/16`) has exhausted its address pool, or leftover network state from a previous session conflicts with the current subnet configuration.

## Fix Procedure

```bash
# Step 1: Kill stale dockerd processes
sudo pkill -9 dockerd
sudo rm -f /var/run/docker.pid /run/docker.pid

# Step 2: Remove stale network database files
sudo rm -rf /var/lib/docker/network/files/*.db 2>/dev/null
sudo rm -rf /var/lib/docker/bridge/* 2>/dev/null

# Step 3: Clean up stale bridge interfaces
sudo ip link delete docker0 2>/dev/null
sudo ip link delete docker_gwbridge 2>/dev/null
sudo ip link delete flannel.1 2>/dev/null

# Step 4: Restart Docker
sudo systemctl daemon-reload
sudo systemctl restart docker
sleep 10
systemctl is-active docker  # should return "active"

# Step 5: Redeploy containers (networks need recreation)
cd /home/mkanavi/docker/iacgenie
docker compose down 2>/dev/null
docker network prune -f 2>/dev/null
docker compose up -d
```

## Prevention

Ensure `/etc/docker/daemon.json` uses a non-overlapping subnet:

```json
{
  "default-address-pools": [{
    "base": "10.0.0.0/8",
    "size": 24
  }]
}
```

## Critical Notes

- **CRITICAL:** Docker network cleanup requires full compose restart. After deleting `/var/lib/docker/network`, ALL containers must be recreated — you cannot selectively restart services.
- **Ansible integration:** Add a `docker-network-recovery.yml` playbook that runs before `services.yml`. It should check if Docker is active, and if not, run the recovery procedure above.