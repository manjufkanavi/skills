# Next.js Dockerfile Output Mismatch

**Session:** 2026-08-28. Resume platform webUI Docker build failed because `next.config.js` had `output: 'export'` but the Dockerfile expected `.next/standalone`.

## The Pitfall

When building a Next.js app for Docker deployment:

- `output: 'export'` in `next.config.js` produces a **static HTML export** at `.next/export/`. No Node server.
- The Dockerfile uses `COPY --from=builder /app/.next/standalone ./` and runs `node server.js`.

**These are incompatible.** The build succeeds but the container fails to start because `.next/standalone` doesn't exist.

## The Fix

Change `output: 'export'` to `output: 'standalone'`:
```js
// next.config.js
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',     // NOT 'export' for Docker deployment
  images: { unoptimized: true },  // needed since no Next.js image optimization server
};
module.exports = nextConfig;
```

The `standalone` output produces `.next/standalone/server.js` which the Dockerfile's final stage can run with `node server.js`.

## Checklist for Next.js + Docker
1. ✅ `output: 'standalone'` in next.config.js (NOT `'export'`)
2. ✅ `images: { unoptimized: true }` since there's no Next.js image optimization server in the final container
3. ✅ Dockerfile copies `.next/standalone` and `.next/static`, not `.next/export`
4. ✅ Final stage runs `node server.js` (not serving static files)
