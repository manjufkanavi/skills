# Next.js Dev Server — Cross-Origin Dev Resource Blocking

## Symptom
A Next.js dev server accessed via `http://127.0.0.1:<port>` returns **HTTP 200 but an empty / blank body** — the page is stuck at "Loading…" (the SSR'd initial state never resolves). The dev server log shows:

```
⚠ Blocked cross-origin request to Next.js dev resource /_next/webpack-hmr from "127.0.0.1".
Cross-origin access to Next.js dev resources is blocked by default for safety.
To allow this host in development, add it to "allowedDevOrigins" in next.config.js and restart the dev server:
```

## Cause
Next.js blocks cross-origin access to dev resources (`/_next/webpack-hmr`, JS bundles, the HMR socket) by default for safety. When the browser connects from an origin Next.js doesn't recognize (e.g. `127.0.0.1` while the server thinks it is `localhost`), the client bundle / HMR is blocked, so client-side hydration never completes and the page stays stuck at the SSR'd loading state.

## Fix
Add the host to `allowedDevOrigins` in `next.config.js`:

```js
const nextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ["127.0.0.1"],
  // ...other config
};
```

Then **restart the dev server** — the change does not hot-reload.

## Notes
- Equivalent alternative: access via `http://localhost:<port>` instead of `127.0.0.1` also avoids the block (no config change), but `allowedDevOrigins` is the explicit, portable fix.
- Applies to the Next.js **dev** server specifically, not production builds.
- Distinct from client-side `fetch` CORS (browser → API). This is Next.js blocking its own dev-time static / HMR resources, so it shows up as a blank page even though the request is HTTP 200.
