---
name: nextjs-copy-image-deploy
description: Deploy Next.js frontend changes to a COPY-based image.
tags: [nextjs, docker, deploy, frontend, copy-image, next-start]
---

# Next.js COPY-Based Image Deploy

Deploy changes to a Next.js frontend whose Docker image is **COPY-based**: it
copies in an already-built `.next` output and `node_modules`, then runs
`npx next start`. There is **no build step inside the image**, so frontend edits
must be built on the host/VM first, then `docker compose up -d`.

## Trigger
- User changes a Next.js frontend file and the live site shows no change.
- Deploying to an image that uses `COPY .next` + `CMD ["npx","next","start"]`.
- "Why isn't my frontend change showing up?" after a git commit.

## Core mental model
- **A git commit does not change the running UI.** The image is a static snapshot.
- Frontend changes require: (1) rebuild `.next` on the host where source lives,
  then (2) `docker compose up -d <webui-service>`.
- If the changed file imports other local modules, **those files must also be**
  present in the build context or `next build` fails with `Module not found`.

## Deployment workflow
1. Confirm the image model — read the Dockerfile:

   ```bash
   cat <service-dir>/Dockerfile
   ```

   Look for `COPY .next`, `COPY node_modules`, and a CMD like
   `npx next start -p <port>`. That confirms COPY-based.

2. Ensure every file the changed imports resolve to is in the build context
   (e.g. a new form importing `@/lib/auth-api` and `@/components/ui/otp-input`
   needs both present).

3. Rebuild `.next` on the host/VM (Node version caveat below), then redeploy:

   ```bash
   docker compose -f <compose-file> up -d <webui-service-name>
   ```

## Node version caveat (Next 16)
- Next.js **16 rejects Node <20.9.0**. A VM default `node` may be v18.x and the
  build silently fails. Activate a newer Node before building:

  ```bash
  export PATH='<path-to-node-v20>/bin:$PATH'
  node --version   # confirm >=20.9.0
  ```

- `npx next build` can fail with `ENOENT spawn sh`. Run the local binary
  directly instead:

  ```bash
  NODE20=/path/to/node-v20/bin/node
  "$NODE20" ./node_modules/next/dist/bin/next build > /tmp/build.log 2>&1
  echo "BUILD_EXIT: $?"
  ```

- A `Found lockfile missing swc dependencies, patching...` followed by a
  network error means the swc-patch step needs registry access.

## Verification after deploy
```bash
docker ps --format '{{.Names}}\t{{.Status}}' | grep <webui>
curl -sI http://127.0.0.1:<port>/_next/static/chunks/*.css   # expect 200
```

## Reference file
See `references/webui-deployment.md` for a worked VM example: nvm Node version,
direct-binary build invocation, scp/rsync sync steps, and compose redeploy.
