---
name: service-replacement
description: "Class-level skill for replacing one service/runtime with another on a Docker-compose VM — cleanup old, install new, migrate credentials, configure, start."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
tags: [service-replacement, migration, systemd, docker, zeroclaw, config]
---

# Service Replacement

Pattern for replacing one service/runtime with another on a Docker-composed VM. Covers cleanup, installation, credential migration, config, and service registration.

## Triggers

- User wants to replace an existing service (e.g., "uninstall X, install Y instead")
- One agent/chatbot runtime is being swapped for another
- Legacy infrastructure is being decommissioned in favor of a new tool

## 1. Inventory the Old Service

**Before deleting anything, find and extract all credentials and config:**

```bash
# Find the service's systemd unit
systemctl list-units --type=service | grep -i <service-name>

# Find Docker containers
docker ps --format '{{.Names}}\t{{.Image}}' | grep -i <service>

# Find configuration files
find /home/<user> -maxdepth 3 -name '*.yml' -o -name '*.yaml' -o -name '*.toml' -o -name '*.env' -o -name '*.py' -o -name '*.json' 2>/dev/null | xargs grep -li <service-name> 2>/dev/null | head -20

# Extract hardcoded credentials (CRITICAL STEP — they get deleted with the service!)
grep -r 'TOKEN\|API_KEY\|PASSWORD\|SECRET' /path/to/service/files/
```

**⚠️ Pitfall:** Credentials are often hardcoded in application files (e.g., `bot.py` has `TOKEN=*** **Never delete these files before extracting credentials.**

## 2. Stop & Remove the Old Service

```bash
# Systemd services
sudo systemctl stop <service>.service
sudo systemctl disable <service>.service
sudo rm -f /etc/systemd/system/<service>.service
sudo systemctl daemon-reload

# Docker containers
docker stop <container>
docker rm <container>

# Config/data directories (may have permission issues — use sudo)
sudo rm -rf /home/<user>/<service>-workspace
sudo rm -f /home/<user>/service-script.py /home/<user>/service.log
```

**Known issue:** Docker-created files inside bind-mounted volumes are owned by the container's UID (e.g., `10001`), not the host user. Use `sudo rm -rf` for cleanup.

## 3. Install the New Service

### Prebuilt Binary (preferred — no toolchain needed)

```bash
# Most modern tools offer prebuilt binary installers
curl -fsSL https://<repo>/install.sh | sh -s -- --prebuilt
# or
curl -fsSL https://<repo>/install.sh | sh
# The installer will ask prebuilt vs source — pick prebuilt for speed
```

### From Source (when prebuilt unavailable)

```bash
# Install toolchain first
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y  # Rust
# or other language-specific installers

# Then build
curl -fsSL https://<repo>/install.sh | sh -s -- --source
```

### Via Docker

```bash
# Clone or pull the new image
docker pull <new-image>
# Or build from source
git clone <repo> && cd <repo> && docker build -t <tag> .
```

## 4. Configure the New Service

**Most services use a config file in `~/.<service>/config.toml` or similar.**

### Standard service config structure:

```toml
[providers.models.<provider>.<alias>]
model = "<model-name>"
wire_api = "<api-type>"

[agents.<alias>]
model_provider = "<provider>.<alias>"
...

[channels.<type>.<alias>]
token = "<bot-token>"
# ... provider-specific fields
```

**Configuration steps:**
1. Run `zeroclaw quickstart` (or equivalent) for guided setup
2. Or manually write `~/.<service>/config.toml`
3. **Reuse existing credentials** (bot tokens, API keys) from step 1
4. Verify config: `<service> config show` or equivalent

## 5. Start as a Service

```bash
# Systemd registration
sudo cp <service>.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable <service>.service
sudo systemctl start <service>.service

# Verify
systemctl status <service>.service
```

## 6. Verify

```bash
# Check the service is running
systemctl is-active <service>

# Test the bot/chat endpoint
curl -s http://localhost:<port>/health

# Check model is loaded
curl -s http://10.0.0.7:11434/api/tags

# Test end-to-end
<service> agent -a <alias>  # interactive test
```

## References

- `references/service-replacement-zeroclaw-migration.md` — ZeroClaw replacement of TinyHuman/OpenHuman: full walkthrough, token extraction, config setup