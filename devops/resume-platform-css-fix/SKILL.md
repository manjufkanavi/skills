---
name: resume-platform-css-fix
description: Fix CSS not loading on resume.iacgenie.com — Next.js standalone build missing static chunks
---

# Resume Platform CSS Fix

## Problem
`resume.iacgenie.com` renders with no CSS styling. HTML loads but Tailwind classes have no effect because the CSS file returns 404.

## Root Cause
The Next.js frontend was deployed as a broken standalone build that was missing `.next/static/chunks/` directory. Known issue with Next.js 16 + Tailwind CSS v4 (`@import "tailwindcss"`).

## Fix Steps
1. Add `output: "standalone"` to `webui/next.config.js` (for future Docker builds)
2. Install node_modules on VM with correct platform: `npm install --os=linux --cpu=x64`
3. Rebuild with `npm run build`  
4. Kill old Next.js process on port 3070
5. Start fresh with `npx next start -p 3070` (non-standalone mode properly serves static files)
6. Stop Docker container: `docker stop iacgenie_resume_webui`

## Verification
```bash
curl -sI http://localhost:3070/_next/static/chunks/2omoevi2c_swa.css  # HTTP 1.1 200 OK
curl -s http://localhost:3070/ | grep "bg-background"  # Tailwind classes in HTML
```

## Notes
- Next.js 16 + `output: "standalone"` doesn't properly copy static assets with Tailwind v4
- Use `npx next start` for reliable static file serving  
- VM needs Node v20+ (source ~/.nvm/nvm.sh first)
