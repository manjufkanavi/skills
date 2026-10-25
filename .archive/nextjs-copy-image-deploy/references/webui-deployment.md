# Resume WebUI Deployment (COPY-based image) — worked example

`resume.iacgenie.com` runs on VM `192.168.0.118` (ssh host **newvm**).
Source lives at `/home/mkanavi/docker/iacgenie/resume-platform/webui`.

## Image model (why manual rebuild is needed)
The image `iacgenie-resume-webui:latest` is **COPY-based**, not a build stage.
Dockerfile copies prebuilt output and runs `next start`:

```dockerfile
COPY .next ./.next           # prebuilt output (must contain static/chunks)
COPY node_modules ./node_modules   # host linux x64, matching node:20-alpine
EXPOSE 3070
CMD ["npx", "next", "start", "-p", "3070"]
```

There is **no `npm install` / build step in the image**. So any frontend change
requires rebuilding `.next` on the VM first, then `docker compose up -d webui`.
Committing to git does NOT change the live UI.

## Deploy workflow for frontend changes
1. Sync changed source files to `/home/mkanavi/docker/iacgenie/resume-platform/webui`.
   - Copy **every** file the changed imports resolve to (e.g. a new form that
     imports `@/lib/auth-api` and `@/components/ui/otp-input` needs those files
     present too — missing deps fail the build). Verify with:

       ```bash
       ssh newvm "cd /home/mkanavi/docker/iacgenie/resume-platform/webui && ls src/lib/auth-api.ts src/components/ui/otp-input.tsx"
       ```

2. Rebuild `.next` on the VM (see Node version caveat below).
3. Rebuild + redeploy:

   ```bash
   cd /home/mkanavi/docker/iacgenie/resume-platform
   docker compose -f docker-compose.resume-platform.yml up -d webui api
   ```

## Node version (Next 16 requires >=20.9.0)
VM default `node` is **v18.19.1**, which Next 16 rejects:
`"For Next.js, Node.js version \">=20.9.0\" is required."`
Use the nvm install:

```bash
export PATH='/home/mkanavi/.nvm/versions/node/v20.18.1/bin:$PATH'
```

## Running next build without npx (avoids ENOENT)
`npx next build` on this VM fails with `ENOENT spawn sh`. Run the local binary
directly instead:

```bash
NODE20=/home/mkanavi/.nvm/versions/node/v20.18.1/bin/node
cd /home/mkanavi/docker/iacgenie/resume-platform/webui
"$NODE20" ./node_modules/next/dist/bin/next build > /tmp/next_build.log 2>&1
echo "BUILD_EXIT: $?"
```

Watch for `Found lockfile missing swc dependencies, patching...` — if it then
fails with a network `ETIMEDOUT`, the swc patch step needs registry access.

## Verify
```bash
curl -sI http://127.0.0.1:3070/_next/static/chunks/...css   # expect 200
docker ps --format '{{.Names}}\t{{.Status}}' | grep webui   # expect running
```
