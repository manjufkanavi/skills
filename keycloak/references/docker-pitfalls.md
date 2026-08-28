# Docker Compose & Deployment Pitfalls

## Express secure cookie behind reverse proxy

**Problem:** Session cookies with `secure: true` are dropped by the browser, causing a login loop when the app runs behind nginx/Cloudflare.

**Root cause:** The internal connection between nginx and the Node.js container is HTTP (e.g., `http://127.0.0.1:9091`), not HTTPS. The `secure` flag tells browsers to only send cookies over HTTPS.

**Fix:** Use `secure: false` in Express session config:
```javascript
app.use(session({
  secret: SESSION_SECRET,
  cookie: { httpOnly: true, secure: false, maxAge: 300000 }
}));
```

The external connection (browser → Cloudflare → nginx) IS HTTPS, so the cookie still arrives safely. The internal hop (nginx → container) is HTTP, which is where `secure: true` breaks things.

## Docker HEALTHCHECK wget requires full URL

**Problem:** `HEALTHCHECK CMD wget -qO- /health` always fails with "bad address" error.

**Root cause:** `wget -qO- /health` parses `/health` as a hostname, not a path. Since there's no host specified, wget can't resolve it.

**Fix:** Always include the full URL in the healthcheck command:
```dockerfile
# WRONG (fails):
HEALTHCHECK CMD wget -qO- /health || exit 1

# RIGHT (works):
HEALTHCHECK CMD wget -qO- http://127.0.0.1:9091/health || exit 1
```

## Docker compose orphan containers

After docker compose files change (services added/removed), old containers persist as "orphan" containers consuming resources.

**Fix:** Run `docker compose down` first, then `docker compose up -d` — or run `docker compose up -d --remove-orphans`.

## Docker file system permission issues with overlay2

When mounting host directories into Docker containers that expect writable filesystems (especially OpenBao data directories), the overlay2 filesystem can cause permission errors.

**Fix:** `chmod 777` on the mounted data directory on the host before mounting.
