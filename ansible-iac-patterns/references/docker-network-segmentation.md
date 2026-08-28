# Docker Network Segmentation — 3-Tier Architecture

## When to Use

When hardening a Docker Compose infrastructure for production, implement network segmentation to limit blast radius if a service is compromised. Use after the infrastructure is functional but before production deployment.

## Three-Tier Model

### Tier 1: frontend (internet-facing)
Services exposed through Nginx reverse proxy:
- API services, WebUIs, search engines, page rendering

### Tier 2: backend (data & auth)
Internal data stores, authentication, object storage:
- PostgreSQL, Redis, MinIO, Keycloak, Gitea, OpenBao

### Tier 3: messaging (pub/sub)
Message queue and event bus:
- NSQD, RabbitMQ, Kafka

## Template Pattern

```yaml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
  messaging:
    driver: bridge

services:
  # Backend-only: DB
  postgres:
    networks: [backend]

  # Frontend-only: exposed via Nginx
  searxng:
    networks: [frontend]

  # Multi-network: needs all layers
  lightserp-api:
    networks: [frontend, backend, messaging]
```

## Rules

- Don't use `external: true` for segmentation — define inline in compose file
- Every service must have at least one network (use `networks: []` to skip)
- Port binding (e.g. `127.0.0.1:5432:5432`) does NOT bypass network isolation
- When adding networks, update `depends_on` entries for each layer

## Pitfalls

- **Services on no shared network cannot resolve each other.** Verify: `docker exec <container> nslookup <service-name>`.
- **Docker compose recreates containers on `up -d`** — any manually-added networks via `docker network connect` are lost. Always declare networks in compose file.
- **Container names use underscores** (`iacgenie_postgres`) in `docker ps`, but short service names (`postgres`) resolve via Docker DNS on shared networks.

## Source

Phase 10.2 Security Hardening P1 — ansible-iac-patterns project.
