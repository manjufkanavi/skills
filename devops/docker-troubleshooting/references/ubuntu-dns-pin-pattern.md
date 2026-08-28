# Ubuntu 24.04 DNS Pinning — systemd-resolved + DHCP Conflict

## Problem

systemd-resolved reads DNS from DHCP, which often assigns ISP-poor DNS servers. These resolve intermittently, causing apps to timeout.

## Symptoms

- DNS resolution works sometimes, then fails
- `Temporary failure in name resolution` errors
- Fallback IPs also fail to connect
- `resolvectl status` shows DHCP-assigned DNS IPs (not your preferred resolvers)

## Root Cause

systemd-resolved merges DHCP DNS config with resolved.conf.d drop-ins. The resolved.conf.d files can conflict (alphabetically last wins), and DHCP can override both.

## Fix: Static resolv.conf

```bash
# Break the systemd-resolved managed symlink
sudo rm /etc/resolv.conf

# Create a static file
sudo tee /etc/resolv.conf > /dev/null << 'EOF'
nameserver 1.1.1.1
nameserver 1.0.0.1
EOF

# Verify
nslookup api.telegram.org 1.1.1.1
```

## Why This Works

systemd-resolved expects `/etc/resolv.conf` to be a symlink to `/run/systemd/resolve/stub-resolv.conf`. Breaking the symlink prevents it from being overwritten. Applications read the static file directly.

## DNS in Docker Containers

Docker containers use the host's DNS. If the host has static `/etc/resolv.conf`, containers will too (inherited via `--network host` or via Docker's DNS config). For Docker Compose containers, ensure they don't override DNS with `dns:` settings.