# MCP Server Configuration Patterns

Patterns for configuring MCP servers for multi-agent orchestration.

## Adding MCP Servers

All MCP server additions on this machine require interactive confirmation:

```bash
# Pipe "y" to auto-accept the tool enable prompt
echo "y" | hermes mcp add <name> --command "npx" --args "-y" "<package>"
echo "y" | hermes mcp add <name> --command "<binary>" --args "<arg1>" "<arg2>"
```

## Available MCP Server Packages

### Filesystem Server
```bash
echo "y" | hermes mcp add file-server --command "npx" --args "-y" "@modelcontextprotocol/server-filesystem" "<directory>"
```
- 14 tools: read_file, write_file, search_files, directory_tree, etc.
- Scope to specific directories for security
- Best for: all profiles need file access

### Sequential Thinking
```bash
echo "y" | hermes mcp add sequential-thinking --command "npx" --args "-y" "@modelcontextprotocol/server-sequential-thinking"
```
- 1 tool: sequentialthinking (structured problem-solving)
- Best for: architect, product manager (planning phases)

### GitHub
```bash
echo "y" | hermes mcp add github --command "npx" --args "-y" "@modelcontextprotocol/server-github"
```
- 26 tools: create_issue, create_pull_request, search_code, merge_pull_request, etc.
- Requires GITHUB_PERSONAL_ACCESS_TOKEN in .env
- Best for: developer, tester (repository operations)

### Docker
```bash
echo "y" | hermes mcp add docker --command "docker" --args "run" "--rm" "-i" "-e" "DOCKER_HOST" "mcr.microsoft.com/wingt-jf/mcp-docker-desktop-mcp-server"
```
- Connects to local Docker daemon
- Best for: devops, developer (container management)

## Verification

```bash
# List all configured servers
hermes mcp list

# Test connectivity
hermes mcp test <name>

# Reload after adding servers
hermes mcp reload

# Or in-session: /reload-mcp
```

## Per-Profile Server Assignment

Edit each profile's config.yaml at `~/.hermes/profiles/<name>/config.yaml`:

```yaml
mcp:
  servers:
    - name: file-server        # All profiles
    - name: sequential-thinking  # architect, product_manager only
    - name: github              # developer, tester only
    - name: docker              # devops, developer only
```

## Troubleshooting

### Server won't connect
1. Check the binary/package is available: `which <binary>` or `npx -y <package> --help`
2. Verify permissions on the directory
3. Try the command manually to see the error
4. Check if a new session is needed after configuration

### Too many tools
- MCP adds ALL tools by default. Review the list before enabling.
- For filesystem server, scope to specific directories rather than root.

### Session not picking up new MCP servers
- MCP servers are session-scoped. Start a new session after adding/reloading.
- Or use `hermes mcp reload` to refresh without restart.
