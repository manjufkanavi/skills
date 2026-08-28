---
name: vite
description: Vite / modern frontend build & deploy — ESM import-resolution errors, Docker rebuild-and-redeploy, build cache, bundler (esbuild/Rollup) troubleshooting for React/Vue frontends.
tags: [vite, frontend, esbuild, rollup, webpack, build, docker, react, vue, svelte]
---

# Vite — Frontend Build & Deploy

## Scope
Diagnose and fix Vite / esbuild / Rollup build failures, ESM import-resolution errors, Docker rebuild-and-redeploy pipelines, and bundler configuration issues for modern frontend apps.

## Table of Contents
| Section | Description |
|---------|-------------|
| [Vite Docker Import Resolution](#vite-docker-import-resolution) | Resolve ESM import paths and node_modules inside Docker builds |
| [Vite Frontend Build Troubleshooting](#vite-frontend-build-troubleshooting) | Debug build failures, cache invalidation, chunking, HMR |
| [Next.js Dev Cross-Origin Blocking](#nextjs-dev-cross-origin) | `allowedDevOrigins` fix for 127.0.0.1 dev server returning HTTP 200 with a blank / stuck-"Loading…" body |

## Vite Docker Import Resolution
See archived `vite-docker-import-resolution/` — resolving ESM import paths, node_modules mounting, and Dockerfile build-stage import errors.

## Vite Frontend Build Troubleshooting
See archived `vite-frontend-build-troubleshooting/` — build-cache invalidation, chunk splitting, HMR, and common esbuild/Rollup errors.

## Support Files
Archived references/templates/scripts from the absorbed siblings remain recoverable at `~/.hermes/skills/.archive/`.
