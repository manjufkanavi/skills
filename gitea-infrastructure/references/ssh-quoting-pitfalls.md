# SSH Quoting Pitfalls

## The Problem
SSH + shell + docker exec create a triple-quoting minefield. Each layer needs its own quoting context.

## What FAILS

### Heredoc inside SSH single-quoted command
```bash
ssh host 'cat > /tmp/script.sh' << 'EOF'
docker exec container sh -c "mkdir -p $T && git archive ..."
EOF
# Result: unexpected EOF while looking for matching '
```

### Double-quoted SSH with inner quotes
```bash
ssh host "docker exec container sh -c 'echo $VAR'"
# Result: $VAR expands on host, not container
```

## What WORKS

### A: Base64 (for scripts with loops/vars)
```bash
base64 <<'HEREDOC' > /tmp/script.b64
#!/bin/bash
set -e
docker exec iacgenie-gitea sh -c "mkdir -p /tmp/restore && git archive ..."
HEREDOC
ssh host "cat /tmp/script.b64 | base64 -d | bash"
```

### B: Individual commands (for 1-3 simple steps)
```bash
ssh host 'docker exec container sh -c "mkdir -p /tmp/ri"'
ssh host 'docker exec container git -C /bare/repo read-tree abc123'
```

### C: Python on VM (avoids shell entirely)
```bash
ssh host 'python3 -c "..."'
```

### D: tee + heredoc (for small scripts < 10 lines)
```bash
ssh host 'cat > /tmp/script.sh' << 'HEREDOC'
#!/bin/bash
docker exec container sh -c "command"
HEREDOC
ssh host "bash /tmp/script.sh"
```

## Quick Reference

| Scenario | Pattern |
|---|---|
| 1-3 simple commands | **B** |
| Script needs loops/vars | **A** |
| Small script (< 10 lines) | **D** |
| Avoid shell entirely | **C** |
