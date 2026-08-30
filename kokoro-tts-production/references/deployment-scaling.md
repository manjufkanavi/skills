# Kokoro Production Deployment — Scaling & Concurrency (verified 2026-08-31)

Empirical notes for the hosted `https://kokoro.iacgenie.com` stack on homeserver
192.168.0.116 (docs in `../iacgenie-platform/infra/homeserver/kokoro`).

## Architecture (verified on live host)
- Single `hwdsl2/kokoro-server` container per replica: **cpus=1.0, memory=2g**
  (`NanoCPUs=1000000000`, `HostConfig.Memory=2147483648`).
- Host-mode nginx (`kokoro-nginx`) on :80 load-balances across replicas via an
  `upstream kokoro_backend` block (one `server 127.0.0.1:<port>` per replica).
- Rate limit: `limit_req burst=20 nodelay` at **10 r/s** per client IP (429 on
  overuse). Health endpoint `/health` is exempt from the rate limit.

## Scaling to N replicas
Set `kokoro_replicas: N` in the role defaults, then redeploy with ansible. The
docker-compose template and nginx.conf template both iterate over `kokoro_replicas`
(`range(kokoro_replicas)`), so ports, upstream servers, and `depends_on` are generated
automatically — no manual edits.

```bash
cd ~/.hermes/git_clone_dir/iacgenie-platform/infra/homeserver/kokoro
# edit roles/kokoro/defaults/main.yml: kokoro_replicas: N
ansible-playbook -i inventory.ini playbooks/deploy.yml
```

Each replica gets consecutive host ports: `kokoro_host_port_start` + i for the
i-th replica (0-based).

## PITFALL: stale containers cause HTTP 504 after scaling
After `ansible up -d`, any replica that was already running with the *old* config is
**reused in place** (same container_id, long uptime) rather than recreated. Such a
container can be memory-saturated from before scaling and will start timing out, which
nginx reports to the client as **HTTP 504 Gateway Timeout**.

Symptom: some parallel requests return 200, others 504; `docker stats` shows one
replica near its memory cap while the others sit low.

Fix — force-recreate all replicas for an even baseline:
```bash
cd /home/mkanavi/docker/kokoro && sudo docker compose up -d --force-recreate
```
Then poll each port's `/health` before assuming success.

## Empirical resource usage (observed)
- At rest: ~924 MiB / 2 GiB (~45%) per replica.
- Under load: up to ~1.97 GiB / 2 GiB (~98%) per replica — the container needs room
  to synthesize; watch memory before it OOM-kills or times out.

## Concurrency test pattern
The public endpoint sits behind Cloudflare, which may rate-limit your IP (HTTP 403)
after a burst. To exercise real origin concurrency, hit the **local nginx proxy** over
an SSH session instead — it load-balances across all replicas and bypasses Cloudflare:

```
# On the homeserver (via SSH), POST to http://127.0.0.1:80/v1/audio/speech
# with the bearer key from /home/mkanavi/docker/kokoro/.api_key.
```

Use a ThreadPoolExecutor with N workers and confirm all return HTTP 200 (or expect
504 only if a replica is stale — see the pitfall above).
