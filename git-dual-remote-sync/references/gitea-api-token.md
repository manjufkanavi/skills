# Gitea API Token for Git Push

## Problem

HTTPS push to Gitea requires authentication. Using the admin password in the
URL is fragile. Instead, create a per-user or per-repo access token via the API.

## Steps

1. **Find the admin username and password:**
   ```bash
   docker exec iacgenie-gitea gitea admin user list
   # Check .env file: grep GITEA_ADMIN_PASSWORD /home/mkanavi/docker/iacgenie/.env
   # NOTE: Actual username may differ from .env (admin vs manjufkanavi)
   ```

2. **Create a user-level token via the Gitea API:**
   ```python
   import urllib.request, urllib.parse, json, base64

   admin_user = "manjufkanavi"  # check actual admin name
   admin_pass = "..."           # from .env or gitea-sync remote URL

   encoded_auth = base64.b64encode(f"{admin_user}:{admin_pass}".encode()).decode()
   token_data = json.dumps({
       "name": "git-push-token",
       "scopes": ["write:repository", "read:repository"]
   }).encode()

   req = urllib.request.Request(
       "http://127.0.0.1:3000/api/v1/users/admin/tokens",
       data=token_data,
       headers={"Content-Type": "application/json"},
       method="POST"
   )
   req.add_header("Authorization", f"Basic {encoded_auth}")

   # IMPORTANT: the token field is 'sha1', NOT 'sha'
   with urllib.request.urlopen(req) as r:
       result = json.loads(r.read().decode())
       token = result.get("sha1", "")  # NOT result.get("sha", "")
   ```

3. **Update gitea remotes with the token:**
   ```
   git remote set-url gitea https://<token>@gitea.iacgenie.com/manjufkanavi/<repo>.git
   ```

## Troubleshooting

- **401 Unauthorized**: Wrong username or password. Verify with `docker exec
  iacgenie-gitea gitea admin user list` for the actual admin username.
- **400 Bad Request (token creation)**: Token name already exists. Use a
  different name (e.g. `git-push-v2`).
- **Token field**: Gitea returns `sha1`, not `sha`. Always check `result.get("sha1")`.
- **Scopes**: Use `["write:repository", "read:repository"]` for push access.
